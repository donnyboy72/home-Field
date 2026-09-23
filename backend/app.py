from flask import Flask, jsonify, request
from flask_cors import CORS

#from db import initialize_database


def create_app():
    app = Flask(__name__) #create a flash app instance

    #app.config["DATABASE"] = database/homefield.db

    # if test_config:
    #     app.config.update(test_config)



    # enable CORS for the app
    # CORS will allow vue and flask communicate with each other. 
    # They use different ports so this allows communication between the two.
    CORS(
        app,
        resources={
            #this is what creates the api call for vue to access the backend.
            r"/api/*": {
                "origins": "http://localhost:5173",
            }
        },
    )

    #initialize_database(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)