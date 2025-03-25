from app import create_app, db
from app.models import User, Property, Agent

app = create_app()

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # Add a test user
    user = User(name='Test User', email='test@example.com', user_type='landlord')
    user.set_password('password123')
    db.session.add(user)

    # Add test properties
    prop1 = Property(
        title='Cozy Apartment in Tirana',
        price=75000.0,
        location='Tirana',
        beds=2,
        baths=1,
        size=800,
        image_url='https://via.placeholder.com/600x220',
        purpose='buy',
        user_id=1
    )
    prop2 = Property(
        title='Beachfront Villa in Vlorë',
        price=1500.0,
        location='Vlorë',
        beds=3,
        baths=2,
        size=1200,
        image_url='https://via.placeholder.com/600x220',
        purpose='rent',
        user_id=1
    )
    db.session.add(prop1)
    db.session.add(prop2)

    # Add test agents
    agent1 = Agent(
        name='Ana Kovaçi',
        agency='Elite Properties Albania',
        location='Tirana',
        specialty='luxury',
        sales=32,
        rating=4.8,
        reviews=25,
        image_url='https://randomuser.me/api/portraits/women/1.jpg'
    )
    agent2 = Agent(
        name='Besnik Rama',
        agency='Coastal Realty Group',
        location='Durrës',
        specialty='buying',
        sales=45,
        rating=5.0,
        reviews=18,
        image_url='https://randomuser.me/api/portraits/men/2.jpg'
    )
    db.session.add(agent1)
    db.session.add(agent2)

    db.session.commit()
    print("Database seeded with sample data!")
