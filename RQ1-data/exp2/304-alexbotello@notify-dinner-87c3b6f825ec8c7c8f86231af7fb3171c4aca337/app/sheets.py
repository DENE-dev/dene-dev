import os
import json
import random
import requests
from datetime import datetime

from googleapiclient.discovery import build
from google.oauth2 import service_account

import push
import settings


def get_weekly_recipes():
    recipes = randomly_select_recipes()
    if recipes is None:
        return push.notification("Oops, something went wrong. Please check app")

    full_msg = ""
    for i, recipe in enumerate(recipes):
        num = i + 1
        _, name, ingredients, _, url = recipe
        try:
            update_google_sheet_last_ate(recipe)
        except AssertionError:
            error = "App failed to update Last Ate for {name}"
            push.notification(error)

        full_msg += f"{num}. {name}\n\n{ingredients}\n\n{url}\n\n"

    push.notification(message)
    return "ok"


def randomly_select_recipes():
    recipes = get_google_sheet_recipes()
    random.shuffle(recipes)

    return make_selections(recipes)


def make_selections(recipes, count=3):
    """
    grabs `count` number of recipes that have gone
    atleast two weeks without being selected
    """
    selected_recipes = []
    for recipe in recipes:
        if len(selected_recipes) == count:
            break
        has_been_two_weeks = check_time_range(recipe)
        if has_been_two_weeks:
            selected_recipes.append(recipe)
    return selected_recipes or None


def check_time_range(recipe):
    last_ate = 3
    recipe_last_ate = recipe[last_ate]
    if recipe_last_ate == "":
        return True

    last_ate = datetime.strptime(recipe_last_ate, "%Y-%m-%d %H:%M:%S")
    time_between = datetime.now() - last_ate
    if time_between.days > 14:
        return True
    return False


def update_google_sheet_last_ate(recipe):
    credentials = service_account.Credentials.from_service_account_info(
        build_credentials(), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    cell = recipe[0]
    sheet_range = settings.GOOGLE_SHEET_RANGE
    update_range = f"{sheet_range}!D{cell}"
    values = [[str(datetime.now()).split(".")[0]]]

    service = build("sheets", "v4", credentials=credentials)
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range=update_range,
            valueInputOption="RAW",
            body={"values": values},
        )
        .execute()
    )
    updatedRows = result.get("updatedRows")
    assert updatedRows == 1


def get_google_sheet_recipes():
    credentials = service_account.Credentials.from_service_account_info(
        build_credentials(), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.GOOGLE_SHEET_ID, range=settings.GOOGLE_SHEET_RANGE)
        .execute()
    )
    return sheet.get("values")


def build_credentials():
    """ Manually build google credentials instead of storing a service account
    json file inside the codebase
    """
    service_account_email = settings.SERVICE_ACCOUNT_EMAIL
    credentials = {
        "type": "service_account",
        "project_id": settings.GOOGLE_SHEET_PROJECT_ID,
        "private_key_id": settings.GOOGLE_SHEET_SERVICE_ACCOUNT_KEY_ID,
        "private_key": settings.GOOGLE_SHEET_PRIVATE_KEY,
        "client_email": service_account_email,
        "client_id": settings.GOOGLE_SHEET_CLIENT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/google-sheets%40{service_account_email}",
    }
    return credentials