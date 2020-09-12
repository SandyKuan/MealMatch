from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import pymongo
import gridfs
import json
import codecs
import requests
import os

app = Flask(__name__)


client = pymongo.MongoClient("mongodb+srv://User:a0933591611@cluster0-eufp8.gcp.mongodb.net/test?retryWrites=true&w=majority")
db = client.test
db = client["MealMatch"]
# collection = db["Categories"]
fs = gridfs.GridFS(db)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

UPLOAD_FOLDER = 'html/static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_data():
    data = request.get_data().decode("utf-8")
    # data = request.get_data()
    # data = json.loads(str(request.data, encoding = "utf-8"))
    return data

@app.route("/")
def index():
    return render_template("index.html")

# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods=["POST","GET"])
def upload_information():
    # get current image file
    img_file = request.files['img']
    # get Content Type and File Name of current image
    content_type = img_file.content_type
    filename = secure_filename(img_file.filename)   

    # save to GridFS my image
    # fields <-- recive the id of just saved image
    fields = fs.put(img_file, content_type=content_type, filename=filename)
    # store the filename and _id to another database
    # so here we can much morea easaly get image from our GridFS
    city = request.values.get("city")  
    region = request.values.get("region")  
    postal_code = request.values.get("postal_code")  
    country = request.values.get("country")  
    db['information'].insert({ "filename": filename, "fields": fields, "city":city, "region":region, "postal_code":postal_code, "country":country, "status":"active"})  

    # db['images_test'].insert({"filename": filename, "fields": fields, "status":"active"})

    # save image to file
    res = fs.get(fields).read()
    name = '%s.jpg' % fields
    with open(os.path.join(app.config['UPLOAD_FOLDER'], name), 'wb') as outfile:
      outfile.write(res)
    _id = ObjectId()
    # print(_id)
    return render_template("user_interface.html",imageId=fields, _id=fields)

@app.route('/get_image/<imgId>', methods = ['GET'])
def get_image(imgId):

   #image = db['images'].find_one({"fields": ObjectId(imgId)})
   # try to get just a first image _id and fing it at GridFS files
    image = fs.get(ObjectId(imgId))
   
    response = make_response(image.read())
    # response.mimetype = 'image/jpeg'
    response.headers.set('Content-Disposition', 'attachment', filename='%s.jpg' % imgId)
    return response

@app.route("/questions", methods = ['GET'])
def questions():
    try:
        questions = db.information.find({"status":"finish"})
        return render_template('user_interface.html', questions = questions)
    except Exception as e:
        return dumps({'error' : str(e)})

@app.route("/user_interface", methods=["POST","GET"])
def user_interface():
    return render_template("user_interface.html")

@app.route("/worker_1")
def worker_interface():
    return render_template("worker_1.html")
    


@app.route("/get_result", methods=["POST","GET"])
def get_result():
    data = get_data()
    # print(data)
    res = db.information.find_one({'fields':ObjectId(data)})
    # print(res)    
    results = res["results"]
    ans = []
    for r in results:
        name = r["Name"]
        address = r["Address"]
        ans.append([name, address])


    # res = [
    #     {
    #         "status":r["status"], 
    #         # "image":r["image"], 
    #         "id":str(r["_id"]),
    #         "results":r.get("results", []),
    #     } 
    #     for r in db.information.find({})
    # ]
    return json.dumps(ans)


if __name__ == "__main__":
    app.run(debug=True)