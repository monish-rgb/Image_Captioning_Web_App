from flask import Flask, request, redirect,send_file,render_template,url_for,Response
import os,io,re
import sys
from google.cloud import storage
import requests
from io import BytesIO
from PIL import Image
import google.generativeai as genai
import base64

app = Flask(__name__)

#GEMINI AI Studio API 
genai.configure(api_key="AIzaSyDkHSgrWxsTzmYwaev5VNaqfEc2Sq8uLuM")

# Creating the LLM model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

@app.get('/')
def index():
    html_form="""
    <body style="background-color:powderblue;">
    <form method="post" enctype="multipart/form-data" action="/upload" method="post">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
</form>
"""
    #call the function for GET /files and loop through the list to add to the HTML
    for file in list_files():
        html_form += "<li><a href=\"/image/" + file + "\">" + file + "</a></li>"
    return html_form

#in POST /upload - lookup how to extract uploaded file and save uploaded file in the desired bucket in google cloud
@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file'] 

    if not file:
      return "No file uploaded.", 400

    # Create a Cloud Storage client.
    gcs = storage.Client()
    # Get the bucket that the file will be uploaded to.
    bucket = gcs.get_bucket("bucket_monish_assignment1")
    # Create a new blob and upload the file's content.
    blob = bucket.blob(file.filename)
    blob.upload_from_string(
        file.read(), content_type=file.content_type
    )
    
    #calling get_file_description() function when uploading image into GCS bucket
    x = get_file_description(file.filename)
    print("description",x)
    return redirect('/')
    
#GET /image - storing all the files in a list(files) from the bucket to show all the uploaded files
@app.route('/image')
def list_files():
    files=[]
    storage_client = storage.Client()
    blobs = storage_client.list_blobs("bucket_monish_assignment1")
    for blob in blobs:
        if (blob.name.endswith(".jpeg") or blob.name.endswith(".png") or blob.name.endswith(".jpg")):
            files.append(blob.name)
    print(files)
    return files


@app.route('/image/<filename>')
def get_file(filename):
 
  # Create the image URL
  image = url_for('image_url', filename=filename)
  print("Image_url",image)
  
  # Get the image title from the filename (adjust as needed)
  image_title = filename.split(".")[0]
  # Get Image Description
  des_file = image_title+'.txt'
  storage_client = storage.Client()
  blob = storage_client.bucket("bucket_monish_assignment1").blob(des_file) 
  with blob.open('r') as file_obj:
    des = file_obj.read()

  des_cap = re.split('(:)',des)
  cap = des_cap[0]
  des = des_cap[2]
  return render_template("index.html", image_src=image, title=image_title,description=des,caption=cap)


@app.route('/<filename>')
def image_url(filename):
    image_bytes = get_image(filename)
    return Response(image_bytes, mimetype='image/jpeg')

def get_image(filename):
    try:
      storage_client = storage.Client()
      blob = storage_client.bucket("bucket_monish_assignment1").blob(filename)
      file_obj = io.BytesIO()
      blob.download_to_file(file_obj)
      file_obj.seek(0)
      return file_obj.read()
    except Exception as e:
        print(f"Error processing favicon.ico: {e}")
 

def get_file_description(filename):

    storage_client = storage.Client()
    blob = storage_client.bucket("bucket_monish_assignment1").blob(filename)
    # Download the image directly to a BytesIO object
    image_data = BytesIO()
    blob.download_to_file(image_data)
    # Create a PIL Image object from the BytesIO object
    image = Image.open(image_data)
    result = model.generate_content(
    [image, "\n\n", "Give me caption for this image and also give brief description of this image where caption and decription separated by :"]
)
    print(f"{result.text=}")
    info_name=os.path.basename(filename).split('.')[0]
    info_name=info_name+".txt"
    blob1 = storage_client.bucket("bucket_monish_assignment1").blob(info_name)
    blob1.upload_from_string(result.text,content_type="text/plain")
    
    return result.text


if __name__ == "__main__":
    app.run(debug=True)
    
