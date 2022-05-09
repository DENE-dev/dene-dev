from datetime import datetime
import json
import os
import io

print("Birthday Logger\n\n1. Add data\n2. Print data")
choice = input("Enter your choice (1, 2) :  ")
file_name = "birthdays.json"
empty_dict = {}

# Dictionaries: Key-Value pairs
if os.path.isfile(file_name) and os.access(file_name, os.R_OK):
    if os.stat(file_name).st_size != 0:
        with open(file_name, "r") as file:
            data = json.load(file)
    else:
        with open(file_name, "w") as file:
            json.dump(empty_dict, file, indent=4)
else:
    with open(file_name, "w") as file:
        json.dump(empty_dict, file, indent=4)
        


def sort_dict_by_date(key):
    date = data.get(key)
    return datetime.strptime(date, "%d/%m")
    

if choice == "1":  # Add data
    name = input("Enter the name: ")
    date = input("Enter the date in DD/MM format: ")
    data[name] = date
    with open("birthdays.json", "w") as file:
        json.dump(data, file, indent=4)


elif choice == "2":
    sorted_data = sorted(data, key=sort_dict_by_date)
    print("\nBirthday Log:")
    for element in sorted_data:
        date = data.get(element)
        print(f"{element}\t{date}")

else:
    print("You have entered a wrong choice")