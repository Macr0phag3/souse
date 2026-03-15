from flask import Flask, request, render_template, redirect, jsonify, url_for
import pickle
import base64
import uuid

app = Flask(__name__)

def waf(func):
    if func.__name__ in ['before_request_funcs', 'after_request_funcs', 'teardown_request_funcs', 'error_handler_spec']:
        raise pickle.UnpicklingError('Nonono')
    return func

class Book:
    def __init__(self, name, species) -> None:
        self.name = name
        self.species = species
        self.uuid = uuid.uuid4()

    def __repr__(self):
        return f'name:{self.name}, species:{self.species},uuid:{self.uuid}'

class Bookshop:
    def __init__(self) -> None:
        self.books = []

    def create_book(self, name, species) -> None:
        book = Book(name, species)
        self.books.append(book)

    def get_book(self, book_uuid) -> Book | None:
        for book in self.books:
            if str(book.uuid) == book_uuid:
                return book
        return None

    def sell_book(self, book_uuid) -> str | None:
        book = self.get_book(book_uuid)
        if book is not None:
            self.books.remove(book)
            serialized_book = base64.b64encode(pickle.dumps(book)).decode("utf-8")
            return serialized_book
        return None

    def check_book(self, serialized_book) -> bool:
        serialized_data = base64.b64decode(serialized_book)
        @waf
        def load_book(data):
            return pickle.loads(data)

        book = load_book(serialized_data)
        
        if isinstance(book, Book):
            for i in self.books:
                if i.uuid == book.uuid:
                    return False
            self.books.append(book)
            return True
        return False


bookshop = Bookshop()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_book":
            name = request.form.get("name")
            species = request.form.get("species")
            bookshop.create_book(name, species)
        elif action == "sell_book":
            book_uuid = request.form.get("book_uuid")
            serialized_book = bookshop.sell_book(book_uuid)
        elif action == "check_book":
            serialized_book = request.form.get("serialized_book")
            success = bookshop.check_book(serialized_book)

    return jsonify({"200": 200})

@app.route("/books/create", methods=["POST"])
def create_book():
    name = request.form.get("name")
    species = request.form.get("species")
    bookshop.create_book(name, species)
    return redirect(url_for('index'))

@app.route("/books/<uuid:book_uuid>", methods=["GET"])
def get_book(book_uuid):
    pet = bookshop.get_book(str(book_uuid))
    if pet:
        return jsonify({"name": pet.name, "species": pet.species, "uuid": str(pet.uuid)})
    else:
        return jsonify({"error": "Book not found"}), 404

@app.route("/books/sell/<uuid:book_uuid>", methods=["POST"])
def sell_book(book_uuid):
    serialized_data = bookshop.sell_book(str(book_uuid))
    if serialized_data:
        return jsonify({"serialized_data": serialized_data})
    else:
        return jsonify({"error": "Book not found"}), 404


@app.route("/books/check", methods=["POST"])
def check_book_route():
    serialized_data = request.form.get("serialized_data")
    @waf
    def check_book_func(data):
        return bookshop.check_book(data)

    if check_book_func(serialized_data):
        return jsonify({"200": "home"}), 200
    else:
        return jsonify({"error": "Failed to check book"}), 400

if __name__ == "__main__":
    app.run(port=8888, debug=False, threaded=True)
