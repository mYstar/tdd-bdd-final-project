######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

# spell: ignore Rofrano jsonify restx dbname
"""
Product Store Service with UI
"""
from flask import jsonify, request, abort
from flask import url_for  # noqa: F401 pylint: disable=unused-import
from service.models import Product, Category
from service.common import status  # HTTP Status Codes
from . import app


######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# H O M E   P A G E
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based the data in the body that is posted
    """
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    product.deserialize(data)
    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()

    location_url = url_for("get_products", id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   P R O D U C T S
######################################################################

@app.route("/products", methods=["GET"])
def list_products():
    app.logger.info("Request to List Products...")

    arguments = request.args.to_dict()

    if 'name' in arguments:
        products = Product.find_by_name(arguments["name"])
    elif 'category' in arguments:
        category = Category[arguments["category"]]
        products = Product.find_by_category(category)
    elif 'available' in arguments:
        available = bool(arguments["available"])
        products = Product.find_by_availability(available)
    else:
        products = Product.all()
    
    products_data = [p.serialize() for p in products]
    return jsonify(products_data), status.HTTP_200_OK

######################################################################
# R E A D   A   P R O D U C T
######################################################################

@app.route("/products/<id>", methods=["GET"])
def get_products(id):
    """
    Reads a Product from the db
    This endpoint will read a product from the database using the given id.
    """
    app.logger.info(f"Request to Read Product with id: {id}")

    product = Product.find(id)
    if product is None:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Product with id: {id} does not exist",
        )
    message = product.serialize()

    return jsonify(message), status.HTTP_200_OK

######################################################################
# U P D A T E   A   P R O D U C T
######################################################################

@app.route("/products/<id>", methods=["PUT"])
def update_products(id):
    """
    Updated a Product
    This endpoint will update an existing Product 
    based on the data in the body that is posted.
    """
    app.logger.info(f"Request to update Product with id: {id}")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product.find(id)
    if product is None:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Product with id: {id} does not exist",
        )
    product.deserialize(data)
    product.update()

    message = product.serialize()
    return jsonify(message), status.HTTP_200_OK


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################


@app.route("/products/<id>", methods=["DELETE"])
def delete_products(id):
    """
    Delete a Product
    This endpoint will delete an existing Product 
    with the given id from the database.
    """
    app.logger.info(f"Request to delete Product with id: {id}")
    product = Product.find(id)
    if product is None:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Product with id: {id} does not exist",
        )
    product.delete()
    return '', status.HTTP_204_NO_CONTENT
    