
from dataaccess.data_models import Movie, Booking
from sqlalchemy.orm import Session
from config.langfuse_tracing import traced




class BookingRepository:



    def __init__(self,db:Session):
        self.db = db
        
    @traced()
    def add_booking(self, booking: Booking):
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)
            return booking


    @traced()
    def get_booking_by_id(self, booking_id: int):
        return self.db.query(Booking).filter(Booking.booking_id == booking_id).first()


    @traced()
    def delete_booking(self, booking_id: int):
        booking = self.get_booking_by_id(booking_id)
        if booking:
            self.db.delete(booking)
            self.db.commit()
            return True
        return False



