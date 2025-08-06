import os
import re
import cv2
import boto3
import base64
import time
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify

app = Flask(__name__)
app.secret_key = "supersecretkey"  #you don't need to fill this

# Your AWS credentials
AWS_ACCESS_KEY_ID = 'IAM Access Key'
AWS_SECRET_ACCESS_KEY = 'IAM secret Key'
AWS_REGION = 'Region your bucket in'  
COMPARISON_BUCKET_NAME = 'bucket name' 


s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def compare_faces(source_image_data):
    target_images = get_images_from_bucket()
    for target_image in target_images:
        response = rekognition_client.compare_faces(
            SourceImage={'Bytes': source_image_data},
            TargetImage={'S3Object': {'Bucket': COMPARISON_BUCKET_NAME, 'Name': target_image}},
            SimilarityThreshold=90
        )

        if response['FaceMatches']:
            person_name = extract_person_name(target_image)
            flash(f"{person_name} marked present", 'success')
            return person_name

    flash("No match found.", 'info')
    return None

def get_images_from_bucket():
    try:
        response = s3_client.list_objects_v2(Bucket=COMPARISON_BUCKET_NAME)
        return [content['Key'] for content in response.get('Contents', [])]
    except Exception as e:
        print(f"Error listing images in bucket {COMPARISON_BUCKET_NAME}: {e}")
        flash(f"Error listing images in bucket {COMPARISON_BUCKET_NAME}: {e}", 'danger')
        return []

def extract_person_name(file_name):
    
    return re.sub(r'\.(jpg|jpeg|png)$', '', file_name, flags=re.IGNORECASE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture_image():
    image_data = request.form['image_data']
    image_data = base64.b64decode(image_data.split(',')[1])
    image_name = f'live_capture_{int(time.time())}.jpg'
    file_path = os.path.join('captures', image_name)
    
    with open(file_path, 'wb') as f:
        f.write(image_data)

    with open(file_path, 'rb') as f:
        source_image_data = f.read()

    person_name = compare_faces(source_image_data)
    os.remove(file_path)  

    return jsonify({'message': 'Person Identified as', 'person_name': person_name})

if __name__ == "__main__":
    if not os.path.exists('captures'):
        os.makedirs('captures')
    app.run(debug=True)
