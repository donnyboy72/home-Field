from flask import Flask, jsonify, request
from flask_cors import CORS

#from db import initialize_database


def create_app():
    app = Flask(__name__)

    #app.config["DATABASE"] = database/homefield.db

    # if test_config:
    #     app.config.update(test_config)

    CORS(
        app,
        resources={
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