from app import app, db, User, Property, Agent, slugify

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
        slug=slugify('Cozy Apartment in Tirana'),
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
        slug=slugify('Beachfront Villa in Vlorë'),
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

    # Add sample agents
    agent1 = Agent(
        name='Ana Kovaçi',
        slug=slugify('Ana Kovaçi'),
        email='ana@example.com',
        phone='123456789',
        agency='Elite Properties Albania',
        specialty='Luxury Homes',
        languages='Albanian, English, Italian',
        location='Tirana',
        bio='Experienced agent specializing in luxury homes.',
        photo_url='https://randomuser.me/api/portraits/women/44.jpg'
    )
    agent2 = Agent(
        name='Besnik Rama',
        slug=slugify('Besnik Rama'),
        email='besnik@example.com',
        phone='987654321',
        agency='Coastal Realty Group',
        specialty='Buying',
        languages='Albanian, English, German',
        location='Durrës',
        bio='Helping buyers find the perfect home on the coast.',
        photo_url='https://randomuser.me/api/portraits/men/32.jpg'
    )
    db.session.add(agent1)
    db.session.add(agent2)


    db.session.commit()
    print("Database seeded with sample data!")
