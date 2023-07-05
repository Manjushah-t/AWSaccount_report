import boto3
import os
import requests
import json

def get_secret_value(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    secret_value = response['SecretString']
    secret_dict = json.loads(secret_value)
    return secret_dict

def get_parameter(name):
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']
    
def lambda_handler(event, context):
    # Retrieve the secrets from AWS Secrets Manager
    secrets = get_secret_value('Metadata_confluence_credentials')

    # Retrieve the variables from the secrets
    api_token = secrets['api_token']
    user_mail = secrets['user_mail']

    # Retrieve the variables from Parameter Store
    base_url = get_parameter('/BaseURL')
    space_key = get_parameter('/SpaceKey')
    page_id = get_parameter('/PageID')

    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    # Specify the table name
    table_name = 'Metadata_test'

    # Scan the DynamoDB table to retrieve all items
    response = dynamodb.scan(TableName=table_name)

    # Extract the items from the response
    items = response['Items']
    
    
    # Create an HTML table with the DynamoDB items
    header_row = "<tr>"
    content_rows = ""

    # Generate the header row with attribute names
    for key in items[0].keys():
        header_row += f"<th>{key}</th>"
    header_row += "</tr>"

    # Generate the content rows with attribute values
    for item in items:
        content_row = "<tr>"
        for value in item.values():
            attr_value = value.get('S', '')
            content_row += f"<td>{attr_value}</td>"
        content_row += "</tr>"
        content_rows += content_row

    # Construct the updated page content with the HTML table
    page_content = f"""
    <h2>Metadata from AWS DynamoDB</h2>
    <table>
         <thead>
            {header_row}
        </thead>
        <tbody>
            {content_rows}
        </tbody>
    </table>
    """

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    get_page_url = f"{base_url}/{page_id}?expand=version,body.storage"
    response = requests.get(get_page_url, auth=(user_mail, api_token), headers=headers)

    if response.status_code == 200:
        page_data = response.json()
        existing_version = page_data['version']['number']
        updated_version = existing_version + 1

        # Update the page data with the new content and version
        page_data['body']['storage']['value'] = page_content
        page_data['version']['number'] = updated_version

        update_page_url = f"{base_url}/{page_id}"
        response = requests.put(update_page_url, auth=(user_mail, api_token), headers=headers, json=page_data)

        if response.status_code == 200:
            print("Page updated successfully")
        else:
            print("Error updating page. Error code: " + str(response.status_code))
            

