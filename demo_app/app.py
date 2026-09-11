from flask import Flask, render_template, request

app = Flask(__name__)


# --------------------------------------------------
# FAKE MEMBER DATA
# --------------------------------------------------

members = {
    "12345": {
        "name": "Alex Carter",
        "checking": "1250.00",
        "savings": "4820.50"
    },

    "54321": {
        "name": "Jordan Lee",
        "checking": "980.25",
        "savings": "3100.00"
    },

    # Recoverable condition
    "77777": {
        "name": "Taylor Morgan",
        "checking": "2100.00",
        "savings": "6750.25",
        "show_notice": True
    },

    # Human intervention condition
    "88888": {
        "name": "Morgan Reed",
        "checking": "3500.00",
        "savings": "9200.75",
        "requires_approval": True
    }
}


# --------------------------------------------------
# MEMBER SEARCH
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def search_member():

    if request.method == "POST":

        member_id = request.form.get("member_id")

        member = members.get(member_id)

        if member:

            return render_template(
                "member.html",
                member_id=member_id,
                member=member
            )

        return "Member not found"

    return render_template("search.html")


# --------------------------------------------------
# SIDEBAR PLACEHOLDER PAGES
# --------------------------------------------------

@app.route("/accounts")
def accounts():

    return render_template(
        "placeholder.html",
        page_title="Accounts",
        description=(
            "Account servicing tools are outside the scope "
            "of this automation demo."
        ),
        active_page="accounts"
    )


@app.route("/service-requests")
def service_requests():

    return render_template(
        "placeholder.html",
        page_title="Service Requests",
        description=(
            "Service request workflows are outside the scope "
            "of this automation demo."
        ),
        active_page="service_requests"
    )


@app.route("/activity")
def activity():

    return render_template(
        "placeholder.html",
        page_title="Activity",
        description=(
            "Member activity history is outside the scope "
            "of this automation demo."
        ),
        active_page="activity"
    )


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)