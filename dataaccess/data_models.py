from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Movie(Base):
    __tablename__ = "Movie_Details"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Movie_name = Column(String, index=True)
    Theatre_name = Column(String, index=True)
    Ticket_price = Column(Integer, index=True)
    Language = Column("language", String, index=True, default="Telugu")
    Total_seats = Column("total_seats", Integer, default=100)
    available_seats = Column(Integer, default=100)

    



class Booking(Base):
    __tablename__ = "Booking_Details"
    
    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    movie_name = Column(String, index=True)  # Book by movie name instead of movie_id
    language = Column(String)  # Store the chosen ticket language directly
    seats_to_book = Column(Integer)
    total_amount = Column(Integer)


## DB Models