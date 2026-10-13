from pydantic import BaseModel

from dataaccess.data_models import Booking, Movie

class MovieCreate(BaseModel):
    Movie_name: str
    Theatre_name: str
    Ticket_price: int
    Language: str
    Total_seats: int


    @classmethod
    def from_db(cls, db_model: Movie):
        return cls(
            Movie_name = db_model.Movie_name,
            Theatre_name = db_model.Theatre_name,
            Ticket_price = db_model.Ticket_price,
            Language = db_model.Language,
            Total_seats = db_model.Total_seats
        )


class BookingCreate(BaseModel):
    movie_name: str
    seats_to_book: int
    language: str
    
    @classmethod
    def from_db(cls, db_model: Booking):
        return cls(
            movie_name = db_model.movie_name,
            seats_to_book = db_model.seats_to_book,
            language = db_model.language,
        )





    