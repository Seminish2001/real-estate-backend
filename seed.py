from app import app, db, User, Property

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # Add a test user
    user = User(name='Test User', email='test@example.com', user_type='Landlord')
    user.set_password('password123')
    db.session.add(user)

    # Add test properties
    prop1 = Property(
        title='Cozy Apartment in Tirana',
        price=75000,
        location='Tirana',
        beds=2,
        baths=1,
        size=800,
        image_url='https://via.placeholder.com/600x220',
        purpose='buy',
        property_type='apartment',
        user_id=1
    )
    prop2 = Property(
        title='Beachfront Villa in Vlorë',
        price=1500,
        location='Vlorë',
        beds=3,
        baths=2,
        size=1200,
        image_url='https://via.placeholder.com/600x220',
        purpose='rent',
        property_type='villa',
        user_id=1
    )
    db.session.add(prop1)
    db.session.add(prop2)


    db.session.commit()
    print("Database seeded with sample data!")
