const backendUrl = 'http://127.0.0.1:5000'; // Update with your backend URL

// Handle Add Property
document.getElementById('add-property-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('title', document.getElementById('title').value);
    formData.append('price', document.getElementById('price').value);
    formData.append('location', document.getElementById('location').value);
    formData.append('type', document.getElementById('type').value);
    formData.append('bedrooms', document.getElementById('bedrooms').value);
    formData.append('size', document.getElementById('size').value);
    formData.append('image', document.getElementById('image').files[0]);

    try {
        const response = await fetch(`${backendUrl}/properties`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`, // Add token for authentication
            },
            body: formData,
        });

        if (response.ok) {
            alert('Property added successfully!');
            window.location.href = 'index.html'; // Redirect to homepage
        } else {
            const data = await response.json();
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        console.error('Error adding property:', error);
        alert('An error occurred while adding the property.');
    }
});
