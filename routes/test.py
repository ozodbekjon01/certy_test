from flask import Blueprint, render_template, session, redirect, request, jsonify, url_for
import sqlite3
import random

bp = Blueprint("test", __name__)

# =========================
# LOGIN REQUIRED
# =========================

def login_required():

    if "user_id" not in session:
        return redirect("/auth/login")


# =========================
# START TEST
# =========================

@bp.route("/<int:test_id>/start")
def start_test(test_id):

    check = login_required()

    if check:
        return check

    user_id = session.get("user_id")

    with sqlite3.connect("database.db") as conn:

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        # ACCESS CHECK

        c.execute("""
            SELECT 1
            FROM contracts c
            JOIN offer_tests ot
            ON c.offer_id = ot.offer_id
            WHERE c.user_id = ?
            AND ot.test_id = ?
        """, (user_id, test_id))

        allowed = c.fetchone()

        if not allowed and session.get("role") != "admin":
            return "Sizda ushbu testga kirish huquqi yo'q", 403

        # TEST INFO

        c.execute("""
            SELECT id, name
            FROM tests
            WHERE id = ?
        """, (test_id,))

        test = c.fetchone()

        if not test:
            return "Test topilmadi", 404

        # QUESTIONS

        c.execute("""
            SELECT
                id,
                question_type,
                question,
                image_location,
                comment
            FROM questions
            WHERE test_id = ?
        """, (test_id,))

        rows = c.fetchall()

    if not rows:
        return "Testda savollar mavjud emas", 404

    questions = []

    for row in rows:

        questions.append({

            "id": row["id"],
            "type": row["question_type"],
            "question": row["question"],
            "image": row["image_location"],
            "explanation": row["comment"]

        })

    random.shuffle(questions)

    session["test_id"] = test_id
    session["test_name"] = test["name"]

    session["questions"] = questions
    session["answers"] = {}

    session["current_index"] = 0

    return redirect(
        url_for("test.exam")
    )


# =========================
# EXAM PAGE
# =========================

@bp.route("/exam")
def exam():

    check = login_required()

    if check:
        return check

    if "questions" not in session:
        return redirect("/dashboard")

    return render_template(
        "test/exam.html"
    )


# =========================
# CURRENT QUESTION API
# =========================

@bp.route("/api/current")
def current_question():

    if "questions" not in session:

        return jsonify({
            "finished": True
        })

    questions = session.get("questions", [])

    current_index = session.get(
        "current_index",
        0
    )

    if current_index < 0 or current_index >= len(questions):

        return jsonify({
            "finished": True
        })

    q = questions[current_index]

    with sqlite3.connect("database.db") as conn:

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("""
            SELECT
                id,
                option,
                image_location,
                appropriate,
                is_correct
            FROM options
            WHERE question_id = ?
        """, (q["id"],))

        rows = c.fetchall()

    options = []

    for row in rows:

        options.append({

            "id": row["id"],
            "option_text": row["option"],
            "image": row["image_location"],
            "appropriate": row["appropriate"],
            "is_correct": row["is_correct"]

        })

    # MATCHING

    if q["type"] == "matching":

        right_sides = [

            opt["appropriate"]
            for opt in options
            if opt["appropriate"]

        ]

        random.shuffle(right_sides)

        for opt in options:

            opt["right_side_options"] = (
                right_sides.copy()
            )

    saved_answer = session.get(
        "answers",
        {}
    ).get(str(q["id"]))

    return jsonify({

        "finished": False,

        "index": current_index,

        "total": len(questions),

        "question_ids": [
            x["id"]
            for x in questions
        ],

        "question": {

            "id": q["id"],
            "question_text": q["question"],
            "image": q["image"],
            "type": q["type"],
            "explanation": q["explanation"]

        },

        "options": options,

        "saved_answer": saved_answer

    })


# =========================
# NAVIGATE
# =========================

@bp.route("/api/navigate", methods=["POST"])
def navigate():

    if "questions" not in session:

        return jsonify({
            "success": False
        })

    data = request.json or {}

    index = data.get("index", 0)

    questions = session.get(
        "questions",
        []
    )

    if 0 <= index < len(questions):

        session["current_index"] = index

        return jsonify({
            "success": True
        })

    return jsonify({
        "success": False
    })


# =========================
# SUBMIT ANSWER
# =========================

@bp.route("/api/submit", methods=["POST"])
def submit_answer():

    if "questions" not in session:

        return jsonify({
            "success": False
        })

    data = request.json or {}

    question_id = str(
        data.get("question_id")
    )

    answer = data.get("answer")

    valid_question_ids = [

        str(q["id"])
        for q in session.get(
            "questions",
            []
        )

    ]

    if question_id not in valid_question_ids:

        return jsonify({
            "success": False
        }), 403

    answers = session.get("answers", {})

    answers[question_id] = answer

    session["answers"] = answers

    return jsonify({
        "success": True
    })


# =========================
# CHECK ANSWER
# =========================

@bp.route("/api/check", methods=["GET"])
def check_answer():

    if "questions" not in session:

        return jsonify({
            "success": False
        })

    qid = request.args.get(
        "question_id",
        type=int
    )

    if not qid:

        return jsonify({
            "success": False
        })

    with sqlite3.connect("database.db") as conn:

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("""
            SELECT
                id,
                is_correct,
                appropriate
            FROM options
            WHERE question_id = ?
        """, (qid,))

        rows = c.fetchall()

    # SINGLE + MULTIPLE

    correct_ids = [

        row["id"]
        for row in rows
        if row["is_correct"] == 1

    ]

    # MATCHING

    correct_options = [

        {
            "id": row["id"],
            "appropriate": row["appropriate"]
        }

        for row in rows

    ]

    # TRUE FALSE

    tf_answers = {}

    for row in rows:

        tf_answers[str(row["id"])] = (

            "yes"
            if row["is_correct"] == 1
            else "no"

        )

    return jsonify({

        "success": True,

        "correct_ids": correct_ids,

        "correct_options": correct_options,

        "tf_answers": tf_answers

    })


# =========================
# FINISH TEST
# =========================

@bp.route("/finish")
def finish():

    check = login_required()

    if check:
        return check

    if "questions" not in session:
        return redirect("/dashboard")

    user_id = session.get("user_id")

    test_id = session.get("test_id")

    questions = session.get("questions", [])

    user_answers = session.get("answers", {})

    correct_count = 0
    wrong_count = 0

    with sqlite3.connect("database.db") as conn:

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        for q in questions:

            q_id = q["id"]

            q_type = q["type"]

            answer = user_answers.get(
                str(q_id)
            )

            c.execute("""
                SELECT
                    id,
                    is_correct,
                    appropriate
                FROM options
                WHERE question_id = ?
            """, (q_id,))

            db_options = c.fetchall()

            # =========================
            # SINGLE CHOICE
            # =========================

            if q_type == "single_choice":

                correct_option = next(

                    (
                        opt["id"]
                        for opt in db_options
                        if opt["is_correct"] == 1
                    ),

                    None

                )

                try:

                    if (
                        answer is not None and
                        int(answer) == correct_option
                    ):

                        correct_count += 1

                    else:

                        wrong_count += 1

                except:

                    wrong_count += 1

            # =========================
            # TRUE FALSE MATRIX
            # =========================

            elif q_type == "true_false":

                is_correct = True

                if not isinstance(answer, dict):

                    is_correct = False

                else:

                    for opt in db_options:

                        opt_id = str(opt["id"])

                        correct_value = (

                            "yes"
                            if opt["is_correct"] == 1
                            else "no"

                        )

                        user_value = answer.get(opt_id)

                        if user_value != correct_value:

                            is_correct = False
                            break

                if is_correct:

                    correct_count += 1

                else:

                    wrong_count += 1

            # =========================
            # MULTIPLE CHOICE
            # =========================

            elif q_type == "multiple_choice":

                correct_ids = [

                    opt["id"]
                    for opt in db_options
                    if opt["is_correct"] == 1

                ]

                user_ids = []

                if isinstance(answer, list):

                    user_ids = [

                        int(x)
                        for x in answer

                    ]

                if sorted(correct_ids) == sorted(user_ids):

                    correct_count += 1

                else:

                    wrong_count += 1

            # =========================
            # MATCHING
            # =========================

            elif q_type == "matching":

                is_correct = True

                if not isinstance(answer, dict):

                    is_correct = False

                else:

                    for opt in db_options:

                        opt_id = str(opt["id"])

                        correct_match = opt["appropriate"]

                        user_match = answer.get(opt_id)

                        if user_match != correct_match:

                            is_correct = False
                            break

                if is_correct:

                    correct_count += 1

                else:

                    wrong_count += 1

        total_questions = len(questions)

        percentage = 0

        if total_questions > 0:

            percentage = round(

                (correct_count / total_questions) * 100,

                2

            )

        score = correct_count

        # SAVE ATTEMPT

        c.execute("""
            INSERT INTO attempts (

                user_id,
                test_id,
                score,
                correct_answers,
                wrong_answers,
                percentage

            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (

            user_id,
            test_id,
            score,
            correct_count,
            wrong_count,
            percentage

        ))

        conn.commit()

    # RESULT SESSION

    session["result"] = {

        "test_name": session.get(
            "test_name",
            "IC3 GS6"
        ),

        "total": total_questions,

        "correct": correct_count,

        "wrong": wrong_count,

        "percentage": percentage

    }

    # CLEAR TEST SESSION

    session.pop("questions", None)
    session.pop("answers", None)
    session.pop("current_index", None)
    session.pop("test_id", None)
    session.pop("test_name", None)

    return redirect(
        url_for("test.result_page")
    )


# =========================
# RESULT PAGE
# =========================

@bp.route("/result")
def result_page():

    check = login_required()

    if check:
        return check

    result = session.get("result")

    if not result:
        return redirect("/dashboard")

    return render_template(

        "test/result.html",

        result=result

    )