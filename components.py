from fasthtml.common import *
from monsterui.all import *

# -- Layout shell ----------------------------------------------------------

def Page(title_text, *content, user=None):
    nav_items = [
        Li(A("Assistant", href="/assistant")),
        Li(A("Projects", href="/projects")),
        Li(A("Reviews", href="/tabular-reviews")),
        Li(A("Workflows", href="/workflows")),
    ]
    user_menu = (
        Li(
            A(user.get("email", ""), href="/account"),
            Ul(
                Li(A("Account", href="/account")),
                Li(A("Sign out", hx_post="/logout", hx_target="body")),
            ),
        )
        if user
        else Li(A("Sign in", href="/login"))
    )
    navbar = Nav(
        Div(
            A(
                Strong("OpenHarvey"),
                href="/assistant",
                cls="uk-logo",
            ),
            cls="uk-navbar-left",
        ),
        Div(Ul(*nav_items, cls="uk-navbar-nav"), cls="uk-navbar-center"),
        Div(Ul(user_menu, cls="uk-navbar-nav"), cls="uk-navbar-right"),
        cls="uk-navbar",
        style="padding: 0 24px; border-bottom: 1px solid var(--uk-color-muted-border);",
    )
    return Title(f"{title_text} - OpenHarvey"), navbar, Main(
        *content, cls="uk-container uk-container-xlarge", style="padding-top: 24px; padding-bottom: 48px;"
    )

# -- Auth forms ------------------------------------------------------------

def LoginForm():
    return Card(
        H2("Sign in to OpenHarvey", cls="uk-text-center"),
        Form(
            LabelInput("Email", type="email", name="email", required=True),
            LabelInput("Password", type="password", name="password", required=True),
            Button("Sign in", type="submit", cls=ButtonT.primary + " uk-width-1-1"),
            Div(id="login-error"),
            P(A("Create an account", href="/signup"), cls="uk-text-center uk-text-small"),
            hx_post="/login",
            hx_target="#login-error",
            cls="space-y-4",
        ),
        cls="uk-width-medium uk-margin-auto uk-margin-large-top",
    )

def SignupForm():
    return Card(
        H2("Create your account", cls="uk-text-center"),
        Form(
            LabelInput("Email", type="email", name="email", required=True),
            LabelInput("Display name", type="text", name="display_name"),
            LabelInput("Organisation", type="text", name="organisation"),
            LabelInput("Password", type="password", name="password", required=True, minlength="8"),
            Button("Create account", type="submit", cls=ButtonT.primary + " uk-width-1-1"),
            Div(id="signup-error"),
            P(A("Already have an account? Sign in", href="/login"), cls="uk-text-center uk-text-small"),
            hx_post="/signup",
            hx_target="#signup-error",
            cls="space-y-4",
        ),
        cls="uk-width-medium uk-margin-auto uk-margin-large-top",
    )

# -- Chat components -------------------------------------------------------

def ChatBubble(role, content):
    is_user = role == "user"
    bubble_cls = "uk-card uk-card-body uk-card-small uk-border-rounded " + (
        "uk-card-primary" if is_user else "uk-card-default"
    )
    align = "uk-flex-right" if is_user else "uk-flex-left"
    return Div(
        Div(
            Div(
                P(Strong("You" if is_user else "Harvey"), cls="uk-text-small uk-text-muted"),
                Div(NotStr(render_md(content)) if not is_user else P(content),
                    cls="prose"),
                cls=bubble_cls,
                style="max-width: 80%;",
            ),
            cls=f"uk-flex {align}",
        ),
        cls="uk-margin-small-bottom",
    )

def ChatInput(chat_id=None):
    target = f"/chat/{chat_id}/send" if chat_id else "/chat/new"
    return Form(
        Div(
            Textarea(
                name="message",
                placeholder="Ask Harvey anything about your documents...",
                rows="2",
                cls="uk-textarea uk-border-rounded",
                style="resize: none;",
                id="chat-input",
            ),
            Div(
                Select(
                    *[
                        Optgroup(
                            *[Option(label, value=mid) for mid, label in models.items()],
                            label=provider,
                        )
                        for provider, models in _get_model_options().items()
                    ],
                    name="model",
                    cls="uk-select uk-form-small uk-form-width-medium",
                ),
                Button("Send", type="submit", cls=ButtonT.primary),
                cls="uk-flex uk-flex-right uk-flex-middle gap-2",
                style="margin-top: 8px;",
            ),
            cls="uk-width-1-1",
        ),
        hx_post=target,
        hx_target="#chat-messages",
        hx_swap="beforeend",
        hx_on__after_request="document.getElementById('chat-input').value = ''",
        cls="uk-margin-top",
    )

def _get_model_options():
    from llm import AVAILABLE_MODELS
    return AVAILABLE_MODELS

def EmptyChat():
    return Div(
        Div(
            H2("Harvey", cls="uk-text-center"),
            P("AI-powered legal document analysis", cls="uk-text-center uk-text-muted"),
            cls="uk-flex uk-flex-column uk-flex-center uk-flex-middle",
            style="min-height: 300px;",
        ),
        id="chat-messages",
    )

# -- Project components ----------------------------------------------------

def ProjectCard(project):
    doc_count = len(project.documents) if project.documents else 0
    return Card(
        H4(A(project.name, href=f"/projects/{project.id}")),
        P(project.description or "No description", cls=TextPresets.muted_sm),
        DivFullySpaced(
            P(f"{doc_count} document{'s' if doc_count != 1 else ''}", cls="uk-text-small"),
            P(project.created_at.strftime("%b %d, %Y") if project.created_at else "", cls="uk-text-small uk-text-muted"),
        ),
    )

def ProjectForm():
    return Form(
        LabelInput("Project name", name="name", required=True),
        LabelInput("Description", name="description"),
        Button("Create project", type="submit", cls=ButtonT.primary),
        Div(id="project-error"),
        hx_post="/projects/create",
        hx_target="#project-list",
        hx_swap="afterbegin",
        cls="space-y-4",
    )

# -- Document components --------------------------------------------------

def DocumentRow(doc):
    size_kb = (doc.size_bytes or 0) / 1024
    size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
    return Tr(
        Td(doc.filename),
        Td(doc.file_type or "unknown"),
        Td(size_str),
        Td(doc.created_at.strftime("%b %d, %Y") if doc.created_at else ""),
        Td(
            Button("Delete", hx_delete=f"/documents/{doc.id}", hx_target="closest tr", hx_swap="outerHTML", hx_confirm="Delete this document?", cls=ButtonT.destructive + " uk-button-small"),
        ),
    )

def DocumentUploadForm(project_id=None):
    action = f"/projects/{project_id}/upload" if project_id else "/documents/upload"
    return Form(
        Input(type="file", name="file", accept=".pdf,.docx,.doc,.txt", required=True),
        Button("Upload", type="submit", cls=ButtonT.primary),
        hx_post=action,
        hx_target="#document-table-body",
        hx_swap="afterbegin",
        hx_encoding="multipart/form-data",
    )

# -- Tabular review components --------------------------------------------

def ReviewCard(review):
    return Tr(
        Td(A(review.title or "Untitled", href=f"/tabular-reviews/{review.id}")),
        Td(review.created_at.strftime("%b %d, %Y") if review.created_at else ""),
        Td(
            Button("Delete", hx_delete=f"/tabular-reviews/{review.id}", hx_target="closest tr", hx_swap="outerHTML", hx_confirm="Delete this review?", cls=ButtonT.destructive + " uk-button-small"),
        ),
    )

# -- Workflow components ---------------------------------------------------

def WorkflowCard(wf):
    return Card(
        H4(A(wf.title, href=f"/workflows/{wf.id}")),
        P(f"Type: {wf.type}", cls=TextPresets.muted_sm),
        P(wf.created_at.strftime("%b %d, %Y") if wf.created_at else "", cls="uk-text-small uk-text-muted"),
    )

def WorkflowForm():
    return Form(
        LabelInput("Title", name="title", required=True),
        Div(
            FormLabel("Type"),
            Select(
                Option("Chat", value="chat"),
                Option("Review", value="review"),
                name="type",
                cls="uk-select",
            ),
        ),
        Div(
            FormLabel("Prompt"),
            Textarea(name="prompt_md", rows="4", cls="uk-textarea", placeholder="Enter workflow prompt..."),
        ),
        Button("Create workflow", type="submit", cls=ButtonT.primary),
        hx_post="/workflows/create",
        hx_target="#workflow-list",
        hx_swap="afterbegin",
        cls="space-y-4",
    )
