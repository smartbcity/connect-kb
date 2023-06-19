import json
from io import BytesIO
from dotenv import load_dotenv
from flask import Flask, flash, request, redirect, Response, g
from waitress import serve
import api_tools
from flask_cors import CORS, cross_origin

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
CORS(app)


def get_vectorestore():
    if 'vectorestore' not in g:
        g.vectorestore = api_tools.get_vectorstore()

    return g.vectorestore


@app.teardown_appcontext
def teardown_vectorestore(_):
    g.pop('vectorestore', None)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        if 'metadata' in request.form:
            file_metadata = json.loads(request.form['metadata'])
        else:
            file_metadata = {}

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            print("file found")

            # filename = secure_filename(file.filename) # get filename
            file_content = BytesIO(file.read())

            vectorstore = get_vectorestore()

            raw_text = api_tools.get_pdf_text(file_content)

            # get the text chunks
            text_chunks = api_tools.get_text_chunks(raw_text)

            # create vector store
            metadata = []
            for _ in text_chunks:
                metadata.append(file_metadata.copy())
            vectorstore.add_texts(text_chunks, metadata)

            return Response("Ok.", mimetype='text/plain', status=201)
            # return redirect(url_for('download_file', name=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


@app.route('/ask', methods=['POST'])
@cross_origin()
def ask():
    vectorstore = get_vectorestore()
    response = api_tools.get_conversation_chain(vectorstore, {}, request.json["messages"])({'question': request.json["question"]})
    return Response(response['answer'], mimetype='text/plain', status=201)

if __name__ == '__main__':
    load_dotenv()
    serve(app, host="0.0.0.0", port=9999)