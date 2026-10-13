from pydantic import BaseModel


class Movie(BaseModel):
    Movie_name: str
    Theatre_name: str
    Ticket_price: int
    Language: str = "Telugu"
    Total_seats: int = 100


class BookingCreate(BaseModel):
    movie_name: str
    seats_to_book: int
    language: str