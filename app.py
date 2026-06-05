import csv
import io
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, redirect, url_for, send_file
from drive_client import get_drive_service, list_files, download_file
from parser import extract_text
from summarizer import summarize

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")


@app.route("/")
def index():
    return render_template("index.html", page="home", results=None, error=None)


@app.route("/browse", methods=["POST"])
def browse():
    folder_id = request.form.get("folder_id", "").strip()
    if not folder_id:
        return render_template("index.html", page="home", error="Enter a folder ID.")
    try:
        service = get_drive_service()
        files = list_files(service, folder_id)
        if not files:
            return render_template("index.html", page="home", error="No supported files found.")
        session["folder_id"] = folder_id
        session["files"] = files
        return render_template("index.html", page="browse", files=files, folder_id=folder_id)
    except Exception as e:
        return render_template("index.html", page="home", error=str(e))


@app.route("/download/file/<file_id>")
def download_drive_file(file_id):
    files = session.get("files", [])
    file_info = next((f for f in files if f["id"] == file_id), None)
    if not file_info:
        return redirect(url_for("index"))
    try:
        service = get_drive_service()
        raw = download_file(service, file_info)
        ext = file_info["extension"]
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        return send_file(
            io.BytesIO(raw),
            mimetype=mime_map.get(ext, "application/octet-stream"),
            as_attachment=True,
            download_name=file_info["name"],
        )
    except Exception as e:
        return f"Error downloading file: {e}", 500


@app.route("/summarize", methods=["POST"])
def run_summarize():
    folder_id = session.get("folder_id", "")
    files = session.get("files", [])
    if not files:
        return render_template("index.html", page="home", error="Session expired. Please re-enter folder ID.")
    try:
        service = get_drive_service()
        results = []
        for f in files:
            raw = download_file(service, f)
            text = extract_text(raw, f["extension"])
            summary = summarize(text, f["name"])
            results.append({"name": f["name"], "summary": summary})
        session["results"] = results
        return render_template("index.html", page="results", results=results, folder_id=folder_id)
    except Exception as e:
        return render_template("index.html", page="home", error=str(e))


@app.route("/download/csv")
def download_csv():
    results = session.get("results")
    if not results:
        return redirect(url_for("index"))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["File Name", "Summary"])
    writer.writeheader()
    for row in results:
        writer.writerow({"File Name": row["name"], "Summary": row["summary"]})
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="summaries.csv")


@app.route("/download/pdf")
def download_pdf():
    results = session.get("results")
    if not results:
        return redirect(url_for("index"))
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Document Summaries", ln=True, align="C")
    pdf.ln(4)
    for i, row in enumerate(results, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, f"{i}. {row['name']}", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, row["summary"])
        pdf.ln(4)
    return send_file(io.BytesIO(pdf.output()), mimetype="application/pdf",
                     as_attachment=True, download_name="summaries.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=5000)