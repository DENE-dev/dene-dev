from flask import Flask, render_template, request
import pickle
import pandas as pd

with open(f'model/cuisine_prediction_model.pkl', 'rb') as f:
    model = pickle.load(f)

app = Flask(__name__, template_folder='templates')

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/post")
def get_bot_response():
    userText = request.args.get('msg')
    preprocess_ingredient(userText)
    test_data_features = create_bag_of_words(userText)
    return str(model.predict(test_data_features))

if __name__ == '__main__':
    app.run()