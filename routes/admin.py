from flask import Blueprint, Flask, render_template, session, redirect, request, url_for
from datetime import timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

bp=Blueprint("admin", __name__)

def login_required():
    if "user_id" not in session:
        return redirect("/auth/login")
    if session.get("role") != "admin":
        return redirect("/dashboard")

@bp.route("/")
def admin():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute(" SELECT count(*) from users")
        user_count = c.fetchone()[0]
        c.execute("SELECT count(*) from offers")
        offer_count = c.fetchone()[0]
        c.execute("SELECT count(*) from contracts")
        contract_count = c.fetchone()[0]
        c.execute("SELECT count(*) from tests")
        test_count = c.fetchone()[0]
    return render_template("admin/index.html", user_count=user_count, offer_count=offer_count, contract_count=contract_count, test_count=test_count)

@bp.route("/users")
def users():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, username, role, created_at FROM users")
        users = c.fetchall()
    return render_template("admin/users.html", users=users)

@bp.route("/tests")
def tests():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, image_location FROM tests")
        tests = c.fetchall()
    return render_template("admin/tests.html", tests=tests)

@bp.route("/offers")
def offers():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, offer_name, offer_time, price, discount FROM offers")
        offers = c.fetchall()
    return render_template("admin/offers.html", offers=offers)

@bp.route("/offers/create", methods=["GET", "POST"])
def create_offer():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        if request.method == "POST":
            offer_name = request.form.get("offer_name")
            offer_time = request.form.get("offer_time")
            price = request.form.get("price")
            discount = request.form.get("discount")
            test_ids = request.form.getlist("test_ids[]")
            
            c.execute("INSERT INTO offers (offer_name, offer_time, price, discount) VALUES (?, ?, ?, ?)",
                      (offer_name, offer_time, price, discount))
            offer_id = c.lastrowid
            
            for test_id in test_ids:
                c.execute("INSERT INTO offer_tests (offer_id, test_id) VALUES (?, ?)", (offer_id, test_id))
            
            conn.commit()
            return redirect("/admin/offers")
            
        c.execute("SELECT id, name FROM tests")
        tests = c.fetchall()
    return render_template("admin/create_offer.html", tests=tests)

@bp.route("/contracts")
def contracts():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.id, o.offer_name, u.username, c.contract_date 
            FROM contracts c 
            JOIN offers o ON c.offer_id = o.id 
            JOIN users u ON c.user_id = u.id
        """)
        contracts = c.fetchall()
    return render_template("admin/contracts.html", contracts=contracts)

@bp.route("/contracts/create", methods=["GET", "POST"])
def create_contract():
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        if request.method == "POST":
            user_id = request.form.get("user_id")
            offer_id = request.form.get("offer_id")
            c.execute("INSERT INTO contracts (user_id, offer_id) VALUES (?, ?)", (user_id, offer_id))
            conn.commit()
            return redirect("/admin/contracts")
            
        c.execute("SELECT id, username, role FROM users WHERE role = 'user'")
        users = c.fetchall()
        c.execute("SELECT id, offer_name, price FROM offers")
        offers = c.fetchall()
    return render_template("admin/create_contract.html", users=users, offers=offers)

@bp.route("/users/create", methods=["GET", "POST"])
def create_user():
    check = login_required()
    if check: return check
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        tg_id = request.form.get("tg_id") or None
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash, role, tg_id) VALUES (?, ?, ?, ?)",
                      (username, generate_password_hash(password), role, tg_id))
            conn.commit()
        return redirect("/admin/users")
    return render_template("admin/create_user.html")


@bp.route("/tests/create", methods=["GET", "POST"])
def create_test():
    check = login_required()
    if check: return check
    if request.method == "POST":
        name = request.form.get("name")
        bio= request.form.get("bio")
        image = request.files.get("image")

        image_location = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)

            os.makedirs("static/images", exist_ok=True)

            image_path = os.path.join("static/images", filename)

            image.save(image_path)

            image_location = image_path

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()

            c.execute(
                """
                INSERT INTO tests (name, bio, image_location)
                VALUES (?, ?, ?)
                """,
                (name, bio, image_location)
            )

            conn.commit()

        return redirect("/admin/tests")

    return render_template("admin/create_test.html")

@bp.route("/tests/<int:test_id>/delete")
def delete_test(test_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tests WHERE id = ?", (test_id,))
        conn.commit()
    return redirect("/admin/tests")

@bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
def edit_test(test_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, bio, image_location FROM tests WHERE id = ?", (test_id,))
        test = c.fetchone()

    if request.method == "POST":
        name = request.form.get("name")
        bio = request.form.get("bio")
        image = request.files.get("image")

        image_location = test[3]

        if image and image.filename != "":
            filename = secure_filename(image.filename)

            os.makedirs("static/images", exist_ok=True)

            image_path = os.path.join("static/images", filename)

            image.save(image_path)

            image_location = image_path

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute(
                """
                UPDATE tests
                SET name = ?, bio = ?, image_location = ?
                WHERE id = ?
                """,
                (name, bio, image_location, test_id)
            )
            conn.commit()

        return redirect("/admin/tests")

    return render_template("admin/create_test.html", test=test)




@bp.route(
    "/tests/<int:test_id>/add_questions",
    methods=["GET", "POST"]
)
def add_questions(test_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:

        c = conn.cursor()

        # =========================
        # TEST CHECK
        # =========================

        c.execute(
            "SELECT * FROM tests WHERE id = ?",
            (test_id,)
        )

        test = c.fetchone()

        if not test:
            return "Test not found"

        # =========================
        # POST
        # =========================

        if request.method == "POST":

            question_type = request.form.get(
                "question_type"
            )

            question_text = request.form.get(
                "question_text"
            )

            # =========================
            # QUESTION IMAGE
            # =========================

            image_location = None

            question_image = request.files.get(
                "question_image"
            )

            if (
                question_image and
                question_image.filename != ""
            ):

                os.makedirs(
                    "static/question_images",
                    exist_ok=True
                )

                filename = secure_filename(
                    question_image.filename
                )

                image_path = os.path.join(
                    "static/question_images",
                    filename
                )

                question_image.save(image_path)

                image_location = image_path

            # =========================
            # SAVE QUESTION
            # =========================

            c.execute(
                """
                INSERT INTO questions
                (
                    test_id,
                    question_type,
                    question,
                    image_location
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    test_id,
                    question_type,
                    question_text,
                    image_location
                )
            )

            question_id = c.lastrowid

            # =========================
            # TRUE / FALSE
            # =========================

            if question_type == "true_false":

                options = request.form.getlist("options[]")
                correct_answers = request.form.getlist("correct_answers[]")

                for index, option_text in enumerate(options):

                    if option_text.strip() == "":
                        continue

                    is_correct = 1 if str(index) in correct_answers else 0

                    c.execute("""
                        INSERT INTO options
                        (
                            question_id,
                            option,
                            is_correct
                        )
                        VALUES (?, ?, ?)
                    """, (
                        question_id,
                        option_text,
                        is_correct
                    ))
            # =========================
            # OTHER TYPES
            # =========================

            else:

                options = request.form.getlist(
                    "options[]"
                )

                option_images = request.files.getlist(
                    "option_images[]"
                )

                correct_answers = request.form.getlist(
                    "correct_answers[]"
                )

                appropriates = request.form.getlist(
                    "appropriate[]"
                )

                for index, option_text in enumerate(options):

                    if option_text.strip() == "":
                        continue

                    # =========================
                    # OPTION IMAGE
                    # =========================

                    option_image_location = None

                    if (
                        len(option_images) > index and
                        option_images[index].filename != ""
                    ):

                        os.makedirs(
                            "static/option_images",
                            exist_ok=True
                        )

                        filename = secure_filename(
                            option_images[index].filename
                        )

                        image_path = os.path.join(
                            "static/option_images",
                            filename
                        )

                        option_images[index].save(
                            image_path
                        )

                        option_image_location = image_path

                    # =========================
                    # IS CORRECT
                    # =========================

                    is_correct = 0

                    if str(index) in correct_answers:
                        is_correct = 1

                    # =========================
                    # MATCHING
                    # =========================

                    appropriate = None

                    if (
                        question_type == "matching" and
                        len(appropriates) > index
                    ):

                        appropriate = appropriates[index]

                    # =========================
                    # SAVE OPTION
                    # =========================

                    c.execute(
                        """
                        INSERT INTO options
                        (
                            question_id,
                            option,
                            image_location,
                            is_correct,
                            appropriate
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            question_id,
                            option_text,
                            option_image_location,
                            is_correct,
                            appropriate
                        )
                    )

            conn.commit()

            return redirect(
                url_for(
                    "admin.view_questions",
                    test_id=test_id
                )
            )

    return render_template(
        "admin/add_questions.html",
        test=test,
        test_id=test_id
    )
    
    
@bp.route("/tests/<int:test_id>/view_questions")
def view_questions(test_id):
    check = login_required()
    if check:
        return check

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("SELECT id, name FROM tests WHERE id = ?", (test_id,))
        test = c.fetchone()
        if not test:
            return "Test not found"

        c.execute("""
            SELECT id, question_type, question, image_location
            FROM questions
            WHERE test_id = ?
        """, (test_id,))
        questions = c.fetchall()

        question_data = []

        for q in questions:
            q_id = q[0]

            c.execute("""
                SELECT option, image_location, is_correct, appropriate
                FROM options
                WHERE question_id = ?
            """, (q_id,))
            options = c.fetchall()

            question_data.append({
                "id": q_id,
                "type": q[1],
                "question": q[2],
                "image": q[3],
                "options": options
            })

    return render_template(
        "admin/view_questions.html",
        test=test,
        questions=question_data
    )
    
    
@bp.route("/questions/<int:question_id>/delete")
def delete_question(question_id):
    check = login_required()
    if check:
        return check

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()

    return redirect(request.referrer or "/admin/tests")


@bp.route("/offers/<int:offer_id>/delete")
def delete_offer(offer_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        conn.commit()
    return redirect("/admin/offers")


@bp.route("/contracts/<int:contract_id>/delete")
def delete_contract(contract_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
        conn.commit()
    return redirect("/admin/contracts")


@bp.route("/users/<int:user_id>/delete")
def delete_user(user_id):
    check = login_required()
    if check: return check
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return redirect("/admin/users")
