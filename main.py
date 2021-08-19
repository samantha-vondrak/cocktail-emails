import os
import pandas as pd
import requests
import json
import string


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import imaplib
import email

email_user = os.environ["EMAIL_USER"]
email_password = os.environ["EMAIL_PWD"]
api_key = os.environ["API_KEY"]
api_key = int(api_key)
api_key = str(api_key)


def login_for_email():
    # account credentials
    username = email_user
    password = email_password

    # create an IMAP4 class with SSL
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    # authenticate
    imap.login(username, password)
    return imap


def get_last_email():
    imap = login_for_email()
    status, messages = imap.select("INBOX")

    # selects the last message recieved
    messages = int(messages[0])
    messages_string = str(messages)

    result, data = imap.fetch(messages_string, '(RFC822)')
    raw = email.message_from_bytes(data[0][1])
    raw_from = raw['From']
    inital_sender = raw_from[raw_from.find("<") + 1:raw_from.find(">")]
    imap.logout()
    body = get_text(raw).decode("utf-8")
    return body, inital_sender


def get_text(msg):
    if msg.is_multipart():
        return get_text(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)


# first, get the drink names and ids
def drink_request(ingredient):
    df = requests.get(f'http://www.thecocktaildb.com/api/json/v2/{api_key}/filter.php?i={ingredient}')
    df_text = json.loads(df.text)
    all_drinks_df = pd.DataFrame.from_dict(df_text['drinks'])
    all_drinks_id = list(all_drinks_df['idDrink'])
    return all_drinks_id

# second, get the other ingredients and instructions
def drink_details(ingredient):
    # need to loop through each of the drink ids to get what i need, then put them back together
    details_dfs = []
    all_drinks_id = drink_request(ingredient)
    for drink_id in all_drinks_id:
        print(drink_id)
        details_request = requests.get(f'http://www.thecocktaildb.com/api/json/v2/{api_key}/lookup.php?i={drink_id}')
        details_text = json.loads(details_request.text)
        details_df = pd.DataFrame.from_dict(details_text['drinks'])
        details_dfs.append(details_df)
    details = pd.concat(details_dfs)

    what_you_need = ingredients_and_amounts(details)
    details_instructions = details[['strDrink', 'strAlcoholic', 'strInstructions']]
    details_instructions = details_instructions[details_instructions['strAlcoholic'] == 'Alcoholic']

    what_you_need_with_instructions = pd.merge(details_instructions, what_you_need,
                                               how='inner', on=['strDrink'])
    return what_you_need_with_instructions

def ingredients_and_amounts(details):
    ingredients_list = ['strIngredient1', 'strIngredient2', 'strIngredient3',
                        'strIngredient4', 'strIngredient5', 'strIngredient6',
                        'strIngredient7', 'strIngredient8', 'strIngredient9',
                        'strIngredient10', 'strIngredient11', 'strIngredient12',
                        'strIngredient13', 'strIngredient14', 'strIngredient15']

    amounts_list = ['strMeasure1', 'strMeasure2', 'strMeasure3', 'strMeasure4',
                    'strMeasure5', 'strMeasure6', 'strMeasure7', 'strMeasure8',
                    'strMeasure9', 'strMeasure10', 'strMeasure11', 'strMeasure12',
                    'strMeasure13', 'strMeasure14', 'strMeasure15']
    columns_to_keep = ['strDrink'] + ingredients_list + amounts_list
    drink_ingredient_amount = details[columns_to_keep]

    what_you_need = grocery_list(drink_ingredient_amount, ingredients_list, amounts_list)
    return what_you_need

def grocery_list(drink_ingredient_amount, ingredients_list, amounts_list):
    drink_ingredient = melt_ingredients_amounts(drink_ingredient_amount,
                                                ingredients_list, 'ingredients', 13)
    drink_amount = melt_ingredients_amounts(drink_ingredient_amount, amounts_list,
                                            'amount', 10)
    what_you_need = pd.merge(drink_ingredient, drink_amount, how='inner',
                             on=['strDrink', 'variable']).drop(['variable'], axis='columns')
    what_you_need = what_you_need.sort_values(by=['strDrink'])
    return what_you_need


def melt_ingredients_amounts(drink_ingredient_amount, value_list, value_name, remove_amt):
    df_melted = drink_ingredient_amount.melt(id_vars=['strDrink'],
                                             value_vars=value_list,
                                             value_name=value_name)
    df_melted['variable'] = df_melted['variable'].str[remove_amt:]
    df_melted = df_melted[-df_melted[value_name].isin(['None', "", None])]
    return df_melted


# what to report
def message_to_send(what_you_need_with_instructions):
    possible_drinks = list(what_you_need_with_instructions['strDrink'].unique())
    possible_drinks_count = len(possible_drinks)

    # define the attachments
    instructions_report = what_you_need_with_instructions[['strDrink', 'strInstructions']].drop_duplicates()
    grocery_list_report = what_you_need_with_instructions[['strDrink', 'ingredients', 'amount']].drop_duplicates()

    # send text in email
    mail_message_body = f"There are {possible_drinks_count} drinks have {ingredient_input} as an ingredient. " \
                        f"They are: {possible_drinks}. " \
                        f"Please see the attachments for a grocery list and instructions."
    body = MIMEText(mail_message_body)

    file_instructions = MIMEApplication(instructions_report.to_csv(index=False),
                                        Name="Cocktail Instructions.csv")
    file_grocery_list = MIMEApplication(grocery_list_report.to_csv(index=False),
                                        Name="Cocktail Grocery List.csv")
    return body, file_instructions, file_grocery_list


# send the email with the attachment
# connect with Google's servers
def server_setup_and_login():
    smtp_ssl_host = 'smtp.gmail.com'
    smtp_ssl_port = 465
    server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
    return server


def send_email(ingredient_input, what_you_need_with_instructions, initial_sender):
    # who to send to
    from_addr = email_user
    to_addrs = initial_sender

    message = MIMEMultipart()
    message['subject'] = f'Your cocktail choices for requested ingredient {ingredient_input}'
    message['from'] = from_addr
    message['to'] = to_addrs
    # convert the body to a MIME compatible string
    body, file_instructions, file_grocery_list = message_to_send(what_you_need_with_instructions)
    message.attach(body)
    message.attach(file_instructions)
    message.attach(file_grocery_list)

    # use username or email to log in
    username = email_user
    password = email_password
    server = server_setup_and_login()
    server.login(username, password)

    # send email
    server.sendmail(from_addr, to_addrs, message.as_string())
    print("Message sent!")
    server.quit()


# input email to ask for the list
body, initial_sender = get_last_email()
print(f"You will be emailing {initial_sender} soon!")
head, sep, tail = body.partition("ingredient ")
table = str.maketrans(dict.fromkeys(string.punctuation))  # OR {key: None for key in string.punctuation}
ingredient_input = tail.translate(table).rstrip()
print(f"Requested ingredient is {ingredient_input}")

# output
what_you_need_with_instructions = drink_details(ingredient_input)
send_email(ingredient_input, what_you_need_with_instructions, initial_sender)
