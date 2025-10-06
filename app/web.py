"""Web Blueprint - HTML serving routes."""

from flask import Blueprint, render_template, session, redirect, url_for, current_app

web_bp = Blueprint("web", __name__)


def get_current_user():
    """Get current user email from session."""
    # In production, this would come from Azure AD token
    return session.get("user_email", "guest@tradex.com")


def is_authenticated():
    """Check if user is authenticated."""
    return "user_email" in session


def is_admin():
    """Check if current user is an admin."""
    if not is_authenticated():
        return False
    user_email = get_current_user()
    return user_email in current_app.config.get("ADMIN_EMAILS", [])


@web_bp.context_processor
def inject_user_info():
    """Make user info available to all templates."""
    return {
        "is_admin": is_admin(),
        "user_email": get_current_user() if is_authenticated() else None,
    }


@web_bp.route("/")
def index():
    """Landing page."""
    if is_authenticated():
        return redirect(url_for("web.dashboard"))
    return render_template("index.html")


@web_bp.route("/login")
def login():
    """Login page (for demo - would use Azure AD OAuth in production)."""
    return render_template("login.html")


@web_bp.route("/auth/callback", methods=["POST"])
def auth_callback():
    """Handle login (simplified for demo)."""
    from flask import request

    email = request.form.get("email", "")
    if email and "@" in email:
        session["user_email"] = email
        session.permanent = True
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web_bp.route("/logout")
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for("web.index"))


@web_bp.route("/debug/config")
def debug_config():
    """Debug configuration (remove in production)."""
    from flask import jsonify

    return jsonify(
        {
            "admin_emails": current_app.config.get("ADMIN_EMAILS", []),
            "current_user": get_current_user(),
            "is_admin": is_admin(),
            "is_authenticated": is_authenticated(),
        }
    )


@web_bp.route("/dashboard")
def dashboard():
    """User dashboard."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template("dashboard.html")


@web_bp.route("/request/new")
def new_request():
    """Request type selector page."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template("request_type_selector.html")


@web_bp.route("/requests/new/onboarding")
def new_onboarding_request():
    """New onboarding request form."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template("request_form.html", request_type="onboarding")


@web_bp.route("/requests/new/firewall")
def new_firewall_request():
    """New firewall request form."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template("request_form.html", request_type="firewall")


@web_bp.route("/requests/new/organization")
def new_organization_request():
    """New organization request form (admin only)."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    if not is_admin():
        return render_template("403.html"), 403

    return render_template("request_form.html", request_type="organization")


@web_bp.route("/requests/new/lob")
def new_lob_request():
    """New LOB request form (admin only)."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    if not is_admin():
        return render_template("403.html"), 403

    return render_template("request_form.html", request_type="lob")


@web_bp.route("/requests/new/subscription")
def new_subscription_request():
    """New subscription request form (admin only)."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    if not is_admin():
        return render_template("403.html"), 403

    return render_template("request_form.html", request_type="subscription")


@web_bp.route("/requests")
def requests_list():
    """View all requests."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template("requests.html")


@web_bp.route("/requests/<int:request_id>")
def request_detail(request_id):
    """View request details."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    return render_template(
        "request_detail.html", request_id=request_id, is_user_admin=is_admin()
    )


@web_bp.route("/requests/<int:request_id>/edit")
def edit_request(request_id):
    """Edit a draft request."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    # Check if request exists and is editable
    from app.models import Application

    application = Application.query.get_or_404(request_id)

    # Check authorization
    user_email = get_current_user()
    if application.requested_by != user_email and not is_admin():
        return render_template("403.html"), 403

    # Check if editable
    if not application.is_editable:
        return redirect(url_for("web.request_detail", request_id=request_id))

    return render_template(
        "request_form.html",
        request_id=request_id,
        edit_mode=True,
        request_data=application.to_dict(),
    )


@web_bp.route("/admin")
def admin_panel():
    """Admin panel."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    # Check admin access
    if not is_admin():
        return render_template("403.html"), 403

    return render_template("admin.html")


@web_bp.route("/admin/lookup")
def admin_lookup():
    """Manage lookup data."""
    if not is_authenticated():
        return redirect(url_for("web.login"))

    # Check admin access
    if not is_admin():
        return render_template("403.html"), 403

    return render_template("admin_lookup.html")
