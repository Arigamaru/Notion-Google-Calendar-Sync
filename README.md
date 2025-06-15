# Notion-Google-Calendar-Sync
This app is able to sync your notion and google calendars. PLease read below to see how to use it.

## Software Requirements
You will require all python packages utilised in this code. Download them using the `pip install` command (or pip3 depending on your environment). Most probably if you already worked with python you will only need to install the packages as follows: `pip install streamlit notion-client google-auth-oauthlib google-api-python-client`

## Required Files and Inputs
### Google OAuth Credentials
In order to use this code you will have to establish your own [Google OAuth 2.0 client](https://console.cloud.google.com/welcome) (create it under "Credentials" → "Create OAuth client ID") and then download the client secret .json file. Currently this code only supports only "Desktop App" clients. Rename this file to client_info.json file and upload it into the same directory as the code. 

### Notion API Key
Create a [Notion integration](https://www.notion.so/my-integrations) and then paste the Internal Integration Secret (API Key) into the "Notion API Key" field. It is necessary for you to link this integration to your Notion calendar database (click the three dots in your database and press "Connections" at the very bottom to add your integration). This is necessary because the integration must have access to the specific Notion database and capabilities to read and update.

### Notion Database ID
From your Notion database URL press the three dots and then click "Copy Link". Paste it somewhere and the Notion database ID will be the long alphanumeric string (e.g., abc123def456...). If you are unsure how to find the database ID please refer to some video explaining it. 

## Notion Database Requirements
The target Notion database must have at least these 3 properties named exactly as: 
```
**Property Name**	             **Type**	          **Purpose**
Task	                     Title	          Event/task name
Due Date	             Date	          Date (or datetime) for the event
Shared ID	             Rich Text	          Unique ID to track sync status
```
Alternatively, you can name the properties whatever you want but you have to make appropriate changes to the python code as well. 

### User Manual
On the first run the he app will open a browser window for Google Calendar access consent linked to the OAuth client. You need to login to the email linked to your google calendar yo want to sync.

A token.json file will be created after login so the user does not need to give consent every time. If you delete a token.json file it will regenerate the next time you give OAuth consent.

Two local cache files will be created: 
1. `sync_cache.json` stores last-known synced states so that edits can be tracked (not fully developed)
2. `sync_settings.json` optionally stores tokens and database info (if the user checks the 'Remember Credentials' button).

If a title or date is changed in Notion or Google Calendar, the change is pushed both ways (currently fixing bugs with duplication of events in Google Calendar after events from Google Caledar were synced to Notion and back).

Matching of events is done using a Shared ID as the primary logic, but utilises also title + date fallback logic. Without Shared IDs everytime a sync is performed all events get duplicated. 

Events without time are treated as all-day events (currently trying to fix). Events with time are patched using UTC unless explicitly defined (please change this depending on your timezone).

