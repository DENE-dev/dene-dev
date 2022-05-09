import json

print("Birthday Logger\n\n1. Add data\n2. Print data")
choice = int(input("Enter your choice (1,2) : "))

# Dictonaries
with open("birthdays.json", "r") as file:
    data = json.load(file)

# Adding data
if choice == 1:
    name = input("Enter the name: ")
    date = input("Enter the date (DD/MM): ")
    data[name] = date
    with open("birthdays.json", "w") as file:
        json.dump(data, file, indent=4)

elif choice == 2:
    print("WIP") # Work in progress

else:
    print("You have given an invalid choice!!!")