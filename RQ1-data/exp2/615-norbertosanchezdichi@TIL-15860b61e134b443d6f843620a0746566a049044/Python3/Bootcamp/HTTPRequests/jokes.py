import requests
from random import choice
from pyfiglet import figlet_format
from termcolor import colored

header = figlet_format("DAD JOKE 3000!")
header = colored(header, color = "cyan")

term = input("What would you like to search for? ")
url = "https://icanhazdadjoke.com/search"
res = results.get(
    url, 
    headers = {"Accept": "application/json"},
    params = {"term": term}).json()

num_jokes = res["total_jokes"]
results = res["results"]

if num_jokes > 1:
    print(f"I found {num_jokes} about {term}.  Here's one:")
    print(choice(results))
elif num_jokes == 1:
    print(f"I found one about {term}.  Here's one:")
    print(results[0]["joke"])
else:
    print(f"Sorry, couldn't find a joke with your term: {term}")