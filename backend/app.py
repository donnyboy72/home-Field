from flask import Flask, jsonify, request
from flask_cors import CORS

from db import init_database


def create_app():
    app = Flask(__name__) #create a flash app instance

    # Set the location of the SQLite database file.
    app.config["DATABASE"] = "database/homefield.db"

    # if test_config:
    #     app.config.update(test_config)



    # enable CORS for the app
    # Allow the Vue development server to access Flask API routes.
    # CORS is needed because Vue and Flask run on different ports.
    CORS(
        app,
        resources={
            #this is what creates the api call for vue to access the backend.
            r"/api/*": {
                # Only allow requests from the Vue development server.
                "origins": "http://localhost:5173",
            }
        },
    )

    # Create the database directory and initialize its tables.
    # Refer to db.py for the initialization logic.
    init_database(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)