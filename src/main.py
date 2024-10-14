# main.py
import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
# import openai
from openai import OpenAI
from database import init_db, get_db_connection

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize the database
init_db()

# Set your OpenAI API key
# openai.api_key = os.environ["OPENAI_API_KEY"]
client = OpenAI()

@app.get("/", response_class=HTMLResponse)
async def read_books(request: Request):
    with get_db_connection() as conn:
        books = conn.execute('SELECT * FROM books').fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "books": books})

@app.post("/add_book/")
async def add_book(request: Request, title: str = Form(...), author: str = Form(...), genre: str = Form(...)):
    with get_db_connection() as conn:
        conn.execute('INSERT INTO books (title, author, genre) VALUES (?, ?, ?)', (title, author, genre))
        conn.commit()
    return await read_books(request)  # Await the read_books function

@app.post("/edit_book/")
async def edit_book(request: Request, id: int = Form(...), title: str = Form(...), author: str = Form(...), genre: str = Form(...)):
    with get_db_connection() as conn:
        conn.execute('UPDATE books SET title = ?, author = ?, genre = ? WHERE id = ?', (title, author, genre, id))
        conn.commit()
    return await read_books(request)  # Await the read_books function

@app.post("/delete_book/")
async def delete_book(request: Request, id: int = Form(...)):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM books WHERE id = ?', (id,))
        conn.commit()
    return await read_books(request)  # Await the read_books function

@app.post("/recommend/")
async def recommend_books(request: Request):
    with get_db_connection() as conn:
        books = conn.execute('SELECT * FROM books').fetchall()
    recommendations = generate_recommendations([dict(book) for book in books])
    return templates.TemplateResponse("recommendations.html", {"request": request, "recommendations": recommendations})

@app.post("/recommend_by_genre/")
async def recommend_by_genre(request: Request, genre: str = Form(...)):
    with get_db_connection() as conn:
        books = conn.execute('SELECT * FROM books WHERE genre = ?', (genre,)).fetchall()
    recommendations = generate_recommendations([dict(book) for book in books])
    return templates.TemplateResponse("recommendations.html", {"request": request, "recommendations": recommendations})

# def generate_recommendations(books):
#     # Call the OpenAI API to generate recommendations
#     response = openai.chat.completions.create(
#         model="gpt-4",
#         messages=[
#             {"role": "user", "content": f"Based on these books: {books}, recommend similar books."}
#         ]
#     )
#     return response.choices[0].message.content


def generate_recommendations(books):
    # Prepare a string of book titles and authors for the API request
    book_descriptions = "\n".join([f"{book['title']} by {book['author']}" for book in books])

    # Call the OpenAI API to generate recommendations
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "return data with a using a  Title by Author - Synopsis format"
            },
            {
                "role": "user",
                "content": f"Based on these books:\n{book_descriptions}\nPlease recommend similar books with their titles, authors, and a brief synopsis."
            }
        ]
    )

    # Parse the API response
    recommendations_text = response.choices[0].message.content.strip()

    # Split the recommendations into lines
    recommendation_lines = recommendations_text.split('\n')

    # Organize recommendations into a list of dictionaries
    organized_recommendations = []
    for line in recommendation_lines:
        # Example expected format: "Title by Author - Synopsis"
        if 'by' in line and '-' in line:
            title_author, synopsis = line.split(' - ', 1)
            if 'by' in title_author:
                title, author = title_author.rsplit(' by ', 1)  # Split only on the last occurrence of ' by '
                organized_recommendations.append({
                    'title': title.strip(),
                    'author': author.strip(),
                    'synopsis': synopsis.strip()
                })

    return organized_recommendations
