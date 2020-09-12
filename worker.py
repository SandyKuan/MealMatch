import boto3
import json
from github import Github
import os, os.path
import time
from pymongo import MongoClient
from pprint import pprint
import re

question_pattern = re.compile("<QuestionIdentifier>(?P<q_name>.*?)</QuestionIdentifier>")
answer_pattern = re.compile("<FreeText>(?P<q_name>.*?)</FreeText>")

def get_key():
    with open("D:/Sandy/Course/2nd semester/IST 402_Crowdsourcing and Crowd AI/Assignments/Final project/rootkey.csv", "r") as infile:
        data = [line.strip().split("=")[1] for line in infile]
        access_key = data[0]
        secret_key = data[1]
    return access_key, secret_key

def get_client():
    region_name = 'us-east-1'
    aws_access_key_id, aws_secret_access_key = get_key()
    endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'

    # Uncomment this line to use in production
    #endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'

    client = boto3.client(
      'mturk',
      endpoint_url=endpoint_url,
      region_name=region_name,
      aws_access_key_id=aws_access_key_id,
      aws_secret_access_key=aws_secret_access_key,
    )

    # This will return $10,000.00 in the MTurk Developer Sandbox
    print(client.get_account_balance()['AvailableBalance'])
    return client

def send_hit(client, setting=None):
    if setting is None:
        with open("setting.xml", 'r') as infile:
            setting = infile.read()

    response = client.create_hit(
        MaxAssignments=5,
        LifetimeInSeconds=60*60*60,
        AssignmentDurationInSeconds=60*10,
        Reward='0.1',
        Title='Find a picture given a painting.',
        Keywords='Search Image,Painting,Picture',
        Description= "Given a user painting, you will need to find the most similar image for it.",
        Question=setting,
        QualificationRequirements=[
            {
                "QualificationTypeId": "000000000000000000L0",
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [
                    98
                ],
                "ActionsGuarded": "Accept"
            },
            {
                "QualificationTypeId": "00000000000000000060",
                "Comparator": "EqualTo",
                "IntegerValues": [
                    1
                ],
                "ActionsGuarded": "Accept"
            }
        ],
    )

    return response

def get_github():
    with open("/home/appleternity/workspace/lab/github.key", 'r') as infile:
        data = [line.strip() for line in infile]
    g = Github(data[0], data[1])
    return g

def generate_html(task_id, img_src):
    dir_path = "html"
    with open(os.path.join(dir_path, "worker_interface.template.html"), 'r', encoding='utf-8') as infile:
        template = infile.read()

    result = template.replace("{{img_src}}", img_src).replace("{{task_id}}", task_id)
    
    with open(os.path.join(dir_path, "{}.html".format(task_id)), 'w', encoding='utf-8') as outfile:
        outfile.write(result)

    return os.path.join(dir_path, "{}.html".format(task_id)), result

def extract_result(hit_id, client):
    response = client.list_assignments_for_hit(
       HITId=hit_id,
       AssignmentStatuses=[
           'Submitted',
       ]
    )
    results = []
    for r in response["Assignments"]:
        answer = r["Answer"]
        questions = question_pattern.findall(answer)
        answers = answer_pattern.findall(answer)
        temp = {}
        for question, answer in zip(questions, answers):
            temp[question] = answer
        results.append(temp)
        response = client.approve_assignment(
            AssignmentId=r["AssignmentId"],
        )

    return results

def task_manager():
    mongo = MongoClient()["CrayonSearch"]
    github = get_github().get_repo("appleternity/CrayonSearch")
    client = get_client()
    with open("template_setting.xml", 'r') as infile:
        template_setting = infile.read()

    while True:
        # check task
        results = mongo.query.find({"status":"active"})
        for res in results:
            filename, content = generate_html(task_id=str(res["_id"]), img_src=res["image"])
            github.create_file(filename, "create html file for worker", content)

            url = "https://appleternity.github.io/CrayonSearch/{}".format(filename)
            print(url)
            setting = template_setting.format(url)
            hit_info = send_hit(client, setting)
            mongo.query.update_one({
                "_id":res["_id"]
            }, {
                "$set": {
                    "status":"processing",
                    "hit_id":hit_info["HIT"]["HITId"],
                    "results":[]
                }
            })
        
        # check result
        results = mongo.query.find({"status":"processing"})
        for res in results:
            hit_id = res["hit_id"]
            results = extract_result(hit_id, client)
            if results:
                print("getting {} results for {}".format(len(results), hit_id))
                mongo.query.update_one({
                    "_id":res["_id"]
                }, {
                    "$push": {
                        "results": {
                            "$each": results
                        }
                    }
                })

        # sleep
        time.sleep(30)

def test_mturk():
    client = get_client()
    
    with open("template_setting.xml", 'r') as infile:
        template_setting = infile.read()
    setting = template_setting.format("https://SandyKuan.github.io/Assignment_2_fix.html")

    hit_info = send_hit(client, setting)
    pprint(hit_info) 
    print(hit_info["HIT"]["HITId"]) 

def main():
    task_manager() 
    #test_mturk()

if __name__ == "__main__":
    main()