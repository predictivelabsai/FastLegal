from web.landing import landing_page
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from fasthtml.common import *
from monsterui.all import *
from starlette.responses import RedirectResponse, StreamingResponse
import bcrypt

from db import SessionLocal, User, UserProfile, Project, Document, Chat, ChatMessage, Workflow, TabularReview, TabularCell, init_db
from llm import stream_chat, generate_title, AVAILABLE_MODELS
from components import (
    Page, LoginForm, SignupForm, ChatBubble, ChatInput, EmptyChat,
    ProjectCard, ProjectForm, DocumentRow, DocumentUploadForm,
    ReviewCard, WorkflowCard, WorkflowForm,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# -- App setup -------------------------------------------------------------

hdrs = (
    Theme.blue.headers(),
    Script(src="https://unpkg.com/htmx-ext-sse@2.2.3/sse.js"),
    Style("""
        .prose { line-height: 1.7; }
        .prose p { margin-bottom: 0.5em; }
        .prose ul, .prose ol { margin-left: 1.5em; margin-bottom: 0.5em; }
        .prose pre { background: var(--uk-color-muted-background); padding: 12px; border-radius: 6px; overflow-x: auto; }
        .prose code { font-size: 0.9em; }
        .gap-2 { gap: 8px; }
        .space-y-4 > * + * { margin-top: 16px; }
        body { min-height: 100vh; }
    """),
)

def _auth_before(req, sess):
    auth = req.scope["auth"] = sess.get("user_id", None)
    public = ("/login", "/signup", "/favicon.ico", "/")
    if not auth and req.url.path not in public and not req.url.path.startswith("/static"):
        return RedirectResponse("/login", status_code=303)

beforeware = Beforeware(_auth_before, skip=[r"/favicon\.ico", r"/static/.*", r".*\.css", r".*\.js"])
app, rt = fast_app(before=beforeware, hdrs=hdrs)

def _get_user(sess):
    uid = sess.get("user_id")
    if not uid:
        return None
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == uid).first()
    finally:
        db.close()

def _user_dict(sess):
    u = _get_user(sess)
    return {"id": u.id, "email": u.email, "display_name": u.display_name} if u else None

# -- Auth routes -----------------------------------------------------------

@rt("/")
def index(sess):
    if sess.get("user_id"):
        return RedirectResponse("/assistant", status_code=303)
    return landing_page()

@rt("/login")
def login_page():
    return Title("Sign in - OpenHarvey"), Main(LoginForm(), cls="uk-container uk-container-small")

@rt("/login")
async def login_post(email: str, password: str, sess):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return P("Invalid email or password", cls="uk-text-danger uk-text-small")
        sess["user_id"] = str(user.id)
        return HtmxResponseHeaders(redirect="/assistant")
    finally:
        db.close()

@rt("/signup")
def signup_page():
    return Title("Sign up - OpenHarvey"), Main(SignupForm(), cls="uk-container uk-container-small")

@rt("/signup")
async def signup_post(email: str, password: str, display_name: str = "", organisation: str = "", sess=None):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return P("Email already registered", cls="uk-text-danger uk-text-small")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(email=email, password_hash=pw_hash, display_name=display_name or None, organisation=organisation or None)
        db.add(user)
        db.flush()
        db.add(UserProfile(user_id=user.id))
        db.commit()
        sess["user_id"] = str(user.id)
        return HtmxResponseHeaders(redirect="/assistant")
    finally:
        db.close()

@rt("/logout")
async def logout(sess):
    sess.clear()
    return HtmxResponseHeaders(redirect="/login")

# -- Assistant / Chat routes -----------------------------------------------

@rt("/assistant")
def assistant(sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        chats = db.query(Chat).filter(Chat.user_id == sess["user_id"]).order_by(Chat.created_at.desc()).all()
        chat_links = Ul(
            *[Li(A(c.title or "Untitled chat", href=f"/assistant/chat/{c.id}")) for c in chats],
            cls="uk-list uk-list-divider",
        ) if chats else P("No conversations yet", cls=TextPresets.muted_sm)
    finally:
        db.close()
    return Page(
        "Assistant",
        Grid(
            Card(H3("Chats"), chat_links, cls="uk-width-1-3"),
            Div(EmptyChat(), ChatInput(), cls="uk-width-2-3"),
            cls="uk-grid-medium",
            style="grid-template-columns: 1fr 3fr;",
        ),
        user=user,
    )

@rt("/assistant/chat/{chat_id}")
def chat_view(chat_id: str, sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == sess["user_id"]).first()
        if not chat:
            return RedirectResponse("/assistant", status_code=303)
        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
        chats = db.query(Chat).filter(Chat.user_id == sess["user_id"]).order_by(Chat.created_at.desc()).all()
        chat_links = Ul(
            *[Li(A(c.title or "Untitled chat", href=f"/assistant/chat/{c.id}", cls="uk-text-bold" if c.id == chat_id else "")) for c in chats],
            cls="uk-list uk-list-divider",
        )
        msg_bubbles = [ChatBubble(m.role, m.content) for m in messages]
    finally:
        db.close()
    return Page(
        chat.title or "Chat",
        Grid(
            Card(
                H3("Chats"),
                chat_links,
                cls="uk-width-1-3",
            ),
            Div(
                Div(*msg_bubbles, id="chat-messages"),
                ChatInput(chat_id=chat_id),
                cls="uk-width-2-3",
            ),
            cls="uk-grid-medium",
            style="grid-template-columns: 1fr 3fr;",
        ),
        user=user,
    )

@rt("/chat/new")
async def chat_new(message: str, model: str = None, sess=None):
    db = SessionLocal()
    try:
        chat = Chat(user_id=sess["user_id"], title="New chat")
        db.add(chat)
        db.flush()
        db.add(ChatMessage(chat_id=chat.id, role="user", content=message))
        db.commit()
        chat_id = str(chat.id)
    finally:
        db.close()

    async def event_stream():
        full_response = []
        yield f"event: message\ndata: {_sse_bubble('user', message)}\n\n"
        yield f"event: message\ndata: <div id='assistant-stream'>\n\n"
        history = [{"role": "user", "content": message}]
        async for token in stream_chat(history, model_id=model):
            full_response.append(token)
            escaped = token.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            yield f"event: message\ndata: {escaped}\n\n"
        yield f"event: message\ndata: </div>\n\n"
        content = "".join(full_response)
        db2 = SessionLocal()
        try:
            db2.add(ChatMessage(chat_id=chat_id, role="assistant", content=content))
            title = await generate_title(message, model)
            db2.query(Chat).filter(Chat.id == chat_id).update({"title": title})
            db2.commit()
        finally:
            db2.close()
        yield f"event: redirect\ndata: /assistant/chat/{chat_id}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@rt("/chat/{chat_id}/send")
async def chat_send(chat_id: str, message: str, model: str = None, sess=None):
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == sess["user_id"]).first()
        if not chat:
            return P("Chat not found", cls="uk-text-danger")
        db.add(ChatMessage(chat_id=chat_id, role="user", content=message))
        db.commit()
        prev_msgs = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
        history = [{"role": m.role, "content": m.content} for m in prev_msgs]
    finally:
        db.close()

    full_response = []
    async for token in stream_chat(history, model_id=model):
        full_response.append(token)
    content = "".join(full_response)

    db2 = SessionLocal()
    try:
        db2.add(ChatMessage(chat_id=chat_id, role="assistant", content=content))
        db2.commit()
    finally:
        db2.close()

    return ChatBubble("user", message), ChatBubble("assistant", content)

@rt("/chat/{chat_id}/delete")
async def chat_delete(chat_id: str, sess):
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == sess["user_id"]).first()
        if chat:
            db.delete(chat)
            db.commit()
    finally:
        db.close()
    return HtmxResponseHeaders(redirect="/assistant")

# -- Projects routes -------------------------------------------------------

@rt("/projects")
def projects_page(sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        projects = db.query(Project).filter(Project.user_id == sess["user_id"]).order_by(Project.created_at.desc()).all()
        cards = [ProjectCard(p) for p in projects]
    finally:
        db.close()
    return Page(
        "Projects",
        DivFullySpaced(H2("Projects"), Button("New project", cls=ButtonT.primary, **{"uk-toggle": "target: #new-project-modal"})),
        Div(
            Div(*cards, cls="uk-grid uk-grid-medium uk-child-width-1-3@m") if cards else P("No projects yet. Create one to get started.", cls=TextPresets.muted_sm),
            id="project-list",
        ),
        Div(
            Div(
                Div(
                    Div(H3("New project"), cls="uk-modal-header"),
                    Div(ProjectForm(), cls="uk-modal-body"),
                    cls="uk-modal-dialog",
                ),
                id="new-project-modal",
                cls="uk-modal",
                **{"uk-modal": True},
            ),
        ),
        user=user,
    )

@rt("/projects/create")
async def project_create(name: str, description: str = "", sess=None):
    db = SessionLocal()
    try:
        p = Project(user_id=sess["user_id"], name=name, description=description or None)
        db.add(p)
        db.commit()
        db.refresh(p)
        return ProjectCard(p)
    finally:
        db.close()

@rt("/projects/{project_id}")
def project_detail(project_id: str, sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == sess["user_id"]).first()
        if not project:
            return RedirectResponse("/projects", status_code=303)
        docs = db.query(Document).filter(Document.project_id == project_id).order_by(Document.created_at.desc()).all()
        doc_rows = [DocumentRow(d) for d in docs]
    finally:
        db.close()
    return Page(
        project.name,
        DivFullySpaced(
            Div(H2(project.name), P(project.description or "", cls=TextPresets.muted_sm)),
            Button("Delete project", hx_delete=f"/projects/{project_id}", hx_confirm="Delete this project and all its documents?", cls=ButtonT.destructive),
        ),
        Card(
            H3("Documents"),
            DocumentUploadForm(project_id),
            Table(
                Thead(Tr(Th("Name"), Th("Type"), Th("Size"), Th("Uploaded"), Th(""))),
                Tbody(*doc_rows, id="document-table-body"),
                cls="uk-table uk-table-divider uk-table-hover",
            ) if doc_rows else P("No documents uploaded yet.", cls=TextPresets.muted_sm),
        ),
        user=user,
    )

@rt("/projects/{project_id}")
async def project_delete(project_id: str, sess):
    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.id == project_id, Project.user_id == sess["user_id"]).first()
        if p:
            db.delete(p)
            db.commit()
    finally:
        db.close()
    return HtmxResponseHeaders(redirect="/projects")

@rt("/projects/{project_id}/upload")
async def project_upload(project_id: str, file: UploadFile, sess=None):
    content = await file.read()
    save_dir = UPLOAD_DIR / sess["user_id"] / project_id
    save_dir.mkdir(parents=True, exist_ok=True)
    filepath = save_dir / file.filename
    filepath.write_bytes(content)
    ext = Path(file.filename).suffix.lower().lstrip(".")
    db = SessionLocal()
    try:
        doc = Document(
            project_id=project_id,
            user_id=sess["user_id"],
            filename=file.filename,
            file_type=ext,
            file_path=str(filepath),
            size_bytes=len(content),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return DocumentRow(doc)
    finally:
        db.close()

# -- Standalone documents --------------------------------------------------

@rt("/documents/upload")
async def doc_upload(file: UploadFile, sess=None):
    content = await file.read()
    save_dir = UPLOAD_DIR / sess["user_id"]
    save_dir.mkdir(parents=True, exist_ok=True)
    filepath = save_dir / file.filename
    filepath.write_bytes(content)
    ext = Path(file.filename).suffix.lower().lstrip(".")
    db = SessionLocal()
    try:
        doc = Document(
            user_id=sess["user_id"],
            filename=file.filename,
            file_type=ext,
            file_path=str(filepath),
            size_bytes=len(content),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return DocumentRow(doc)
    finally:
        db.close()

@rt("/documents/{doc_id}")
async def doc_delete(doc_id: str, sess):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == sess["user_id"]).first()
        if doc:
            if doc.file_path and Path(doc.file_path).exists():
                Path(doc.file_path).unlink()
            db.delete(doc)
            db.commit()
    finally:
        db.close()
    return ""

# -- Tabular Reviews -------------------------------------------------------

@rt("/tabular-reviews")
def reviews_page(sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        reviews = db.query(TabularReview).filter(TabularReview.user_id == sess["user_id"]).order_by(TabularReview.created_at.desc()).all()
        rows = [ReviewCard(r) for r in reviews]
    finally:
        db.close()
    return Page(
        "Tabular Reviews",
        DivFullySpaced(
            H2("Tabular Reviews"),
            Div(
                Form(
                    Input(name="title", placeholder="Review title...", cls="uk-input uk-form-small uk-form-width-medium"),
                    Button("New review", type="submit", cls=ButtonT.primary + " uk-button-small"),
                    hx_post="/tabular-reviews/create",
                    hx_target="#review-table-body",
                    hx_swap="afterbegin",
                    cls="uk-flex uk-flex-middle gap-2",
                ),
            ),
        ),
        Table(
            Thead(Tr(Th("Title"), Th("Created"), Th(""))),
            Tbody(*rows, id="review-table-body"),
            cls="uk-table uk-table-divider uk-table-hover",
        ) if rows else P("No reviews yet.", cls=TextPresets.muted_sm),
        user=user,
    )

@rt("/tabular-reviews/create")
async def review_create(title: str = "Untitled Review", sess=None):
    db = SessionLocal()
    try:
        r = TabularReview(user_id=sess["user_id"], title=title or "Untitled Review")
        db.add(r)
        db.commit()
        db.refresh(r)
        return ReviewCard(r)
    finally:
        db.close()

@rt("/tabular-reviews/{review_id}")
def review_detail(review_id: str, sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        review = db.query(TabularReview).filter(TabularReview.id == review_id, TabularReview.user_id == sess["user_id"]).first()
        if not review:
            return RedirectResponse("/tabular-reviews", status_code=303)
        cols = review.columns_config or []
        cells = db.query(TabularCell).filter(TabularCell.review_id == review_id).all()
    finally:
        db.close()
    col_headers = [Th(c.get("name", f"Col {i}")) for i, c in enumerate(cols)] if cols else [Th("No columns configured")]
    return Page(
        review.title or "Review",
        DivFullySpaced(
            H2(review.title or "Untitled Review"),
            Button("Delete", hx_delete=f"/tabular-reviews/{review_id}", hx_confirm="Delete this review?", cls=ButtonT.destructive),
        ),
        Card(
            Table(
                Thead(Tr(Th("Document"), *col_headers)),
                Tbody(Tr(Td("No data yet", colspan=str(len(col_headers)+1))) if not cells else ""),
                cls="uk-table uk-table-divider uk-table-small",
            ),
        ),
        user=user,
    )

@rt("/tabular-reviews/{review_id}")
async def review_delete(review_id: str, sess):
    db = SessionLocal()
    try:
        r = db.query(TabularReview).filter(TabularReview.id == review_id, TabularReview.user_id == sess["user_id"]).first()
        if r:
            db.delete(r)
            db.commit()
    finally:
        db.close()
    return ""

# -- Workflows -------------------------------------------------------------

@rt("/workflows")
def workflows_page(sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        workflows = db.query(Workflow).filter(
            (Workflow.user_id == sess["user_id"]) | (Workflow.is_system == True)
        ).order_by(Workflow.created_at.desc()).all()
        cards = [WorkflowCard(w) for w in workflows]
    finally:
        db.close()
    return Page(
        "Workflows",
        DivFullySpaced(H2("Workflows"), Button("New workflow", cls=ButtonT.primary, **{"uk-toggle": "target: #new-wf-modal"})),
        Div(
            Div(*cards, cls="uk-grid uk-grid-medium uk-child-width-1-3@m") if cards else P("No workflows yet.", cls=TextPresets.muted_sm),
            id="workflow-list",
        ),
        Div(
            Div(
                Div(
                    Div(H3("New workflow"), cls="uk-modal-header"),
                    Div(WorkflowForm(), cls="uk-modal-body"),
                    cls="uk-modal-dialog",
                ),
                id="new-wf-modal",
                cls="uk-modal",
                **{"uk-modal": True},
            ),
        ),
        user=user,
    )

@rt("/workflows/create")
async def workflow_create(title: str, type: str = "chat", prompt_md: str = "", sess=None):
    db = SessionLocal()
    try:
        w = Workflow(user_id=sess["user_id"], title=title, type=type, prompt_md=prompt_md or None)
        db.add(w)
        db.commit()
        db.refresh(w)
        return WorkflowCard(w)
    finally:
        db.close()

@rt("/workflows/{wf_id}")
def workflow_detail(wf_id: str, sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
        if not wf:
            return RedirectResponse("/workflows", status_code=303)
    finally:
        db.close()
    return Page(
        wf.title,
        Card(
            DivFullySpaced(
                H2(wf.title),
                Button("Delete", hx_delete=f"/workflows/{wf_id}", hx_confirm="Delete this workflow?", cls=ButtonT.destructive),
            ),
            P(f"Type: {wf.type}", cls=TextPresets.muted_sm),
            Div(
                H4("Prompt"),
                Div(NotStr(render_md(wf.prompt_md)) if wf.prompt_md else P("No prompt set.", cls=TextPresets.muted_sm), cls="prose"),
            ) if wf.prompt_md or True else "",
        ),
        user=user,
    )

@rt("/workflows/{wf_id}")
async def workflow_delete(wf_id: str, sess):
    db = SessionLocal()
    try:
        wf = db.query(Workflow).filter(Workflow.id == wf_id, Workflow.user_id == sess["user_id"]).first()
        if wf:
            db.delete(wf)
            db.commit()
    finally:
        db.close()
    return HtmxResponseHeaders(redirect="/workflows")

# -- Account ---------------------------------------------------------------

@rt("/account")
def account_page(sess):
    user = _user_dict(sess)
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == sess["user_id"]).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == sess["user_id"]).first()
    finally:
        db.close()
    return Page(
        "Account",
        Grid(
            Card(
                H3("Profile"),
                Form(
                    LabelInput("Display name", name="display_name", value=u.display_name or ""),
                    LabelInput("Organisation", name="organisation", value=u.organisation or ""),
                    P(f"Email: {u.email}", cls=TextPresets.muted_sm),
                    P(f"Plan: {profile.tier if profile else 'Free'}", cls=TextPresets.muted_sm),
                    Button("Save changes", type="submit", cls=ButtonT.primary),
                    Div(id="profile-msg"),
                    hx_post="/account/update",
                    hx_target="#profile-msg",
                    cls="space-y-4",
                ),
            ),
            Card(
                H3("Model settings"),
                Form(
                    Div(
                        FormLabel("Preferred model"),
                        Select(
                            *[
                                Optgroup(
                                    *[Option(label, value=mid, selected=(profile and profile.preferred_model == mid)) for mid, label in models.items()],
                                    label=provider,
                                )
                                for provider, models in AVAILABLE_MODELS.items()
                            ],
                            name="preferred_model",
                            cls="uk-select",
                        ),
                    ),
                    Button("Save", type="submit", cls=ButtonT.primary),
                    Div(id="model-msg"),
                    hx_post="/account/model",
                    hx_target="#model-msg",
                    cls="space-y-4",
                ),
            ),
            cls="uk-grid-medium uk-child-width-1-2@m",
        ),
        Card(
            H3("Danger zone"),
            Button("Sign out", hx_post="/logout", hx_target="body", cls=ButtonT.default),
            Button("Delete account", hx_delete="/account", hx_confirm="This will permanently delete your account. Are you sure?", cls=ButtonT.destructive),
            cls="uk-margin-top",
        ),
        user=user,
    )

@rt("/account/update")
async def account_update(display_name: str = "", organisation: str = "", sess=None):
    db = SessionLocal()
    try:
        db.query(User).filter(User.id == sess["user_id"]).update({
            "display_name": display_name or None,
            "organisation": organisation or None,
        })
        db.commit()
    finally:
        db.close()
    return P("Saved", cls="uk-text-success uk-text-small")

@rt("/account/model")
async def account_model(preferred_model: str, sess=None):
    db = SessionLocal()
    try:
        db.query(UserProfile).filter(UserProfile.user_id == sess["user_id"]).update({
            "preferred_model": preferred_model,
        })
        db.commit()
    finally:
        db.close()
    return P("Model preference saved", cls="uk-text-success uk-text-small")

@rt("/account")
async def account_delete(sess):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == sess["user_id"]).first()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()
    sess.clear()
    return HtmxResponseHeaders(redirect="/login")

# -- Helpers ---------------------------------------------------------------

def _sse_bubble(role, content):
    return f'<div class="uk-margin-small-bottom"><div class="uk-flex {"uk-flex-right" if role == "user" else "uk-flex-left"}"><div class="uk-card uk-card-body uk-card-small uk-border-rounded {"uk-card-primary" if role == "user" else "uk-card-default"}" style="max-width:80%"><p class="uk-text-small uk-text-muted"><strong>{"You" if role == "user" else "Harvey"}</strong></p><p>{content}</p></div></div></div>'

# -- Startup ---------------------------------------------------------------

init_db()
serve(port=5001)
