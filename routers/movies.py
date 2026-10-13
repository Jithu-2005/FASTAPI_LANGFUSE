from fastapi import FastAPI,HTTPException,Depends
from sqlalchemy.orm import Session
from business_logic.models import MovieCreate, BookingCreate
from routers.models import Movie
from business_logic.Movie_logic import Servicelayer
from config.session import get_db
from fastapi import APIRouter

movie_app = APIRouter()




@movie_app.post("/movies")
async def add_Movie(AddMovie: Movie, db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        service_response = service_logic.create_movie(AddMovie)
        return service_response
    except Exception as e:
        # This will print the actual Python/SQLAlchemy error to your terminal!
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)

# Get all Movies
 

@movie_app.get("/movies")
def get_all_movies(db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        service_response = service_logic.get_all_movies()
        return service_response
    except Exception as e:
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)


# Get Movie by ID


@movie_app.get("/movies/{movie_id}")
def get_movie_by_id(movie_id: int, db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        service_response = service_logic.get_movie_by_id(movie_id)
    except Exception as e:
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)
    if not service_response:
        raise HTTPException(status_code=404, detail="Movie not found")
    return service_response


# Update movie details


@movie_app.put("/movies/{movie_id}")
def update_movie(movie_id: int, movie_data: MovieCreate, db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        existing_movie = service_logic.get_movie_by_id(movie_id)
        if not existing_movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        service_response = service_logic.update_movie(movie_id, movie_data)
        return service_response
    except HTTPException:
        raise
    except Exception as e:
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)


# Remove


@movie_app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        service_response = service_logic.delete_movie(movie_id)
    except Exception as e:
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)
    if not service_response:
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"message": "Movie deleted successfully"}


# Book tickets (uses movie_name, not movie_id)


@movie_app.post("/bookings")
def book_tickets(booking_data: BookingCreate, db: Session = Depends(get_db)):
    try:
        service_logic = Servicelayer(db_session=db)
        service_response = service_logic.book_tickets(booking_data)
        return service_response
    except ValueError as e:
        # Movie not found / not enough seats -> client error, not a server error
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"THE REAL ERROR IS: {repr(e)}")
        raise HTTPException(detail=f"Error: {str(e)}", status_code=500)


# Get booking details


@movie_app.get("/bookings/{booking_id}")
def get_booking_details(booking_id: int, db: Session = Depends(get_db)):
    service_logic = Servicelayer(db_session = db)
    booking = service_logic.get_booking_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking details not found")
    return booking


# Cancel a booking


@movie_app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    service_logic = Servicelayer(db_session = db)
    success = service_logic.cancel_booking(booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found or already cancelled")
    return {"message": "Booking cancelled successfully and seats restored"}


#  Return seat counts


@movie_app.get("/movies/{movie_id}/seats")
def get_seat_count(movie_id: int, db: Session = Depends(get_db)):
    service_logic = Servicelayer(db)
    seats = service_logic.get_available_seats(movie_id)
    if seats is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"movie_id": movie_id, "available_seats": seats}


# Filter


@movie_app.get("/movies/language/{language}")
def get_movies_by_language(language: str, db: Session = Depends(get_db)):
    service_logic= Servicelayer(db)
    movies = service_logic.get_movies_by_language(language)
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found for this language")
    return movies
