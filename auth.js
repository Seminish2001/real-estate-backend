const backendUrl = 'http://127.0.0.1:5000'; // Update with your backend URL

// Handle Login
document.getElementById('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch(`${backendUrl}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token); // Save token
            alert('Login successful!');
            window.location.href = 'index.html'; // Redirect to homepage
        } else {
            alert('Login failed: Invalid credentials.');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('An error occurred while logging in.');
    }
});
// Handle Signup
document.getElementById('signup-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('signup-username').value;
    const password = document.getElementById('signup-password').value;

    try {
        const response = await fetch(`${backendUrl}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (response.ok) {
            alert('Signup successful! You can now log in.');
            window.location.href = 'login.html'; // Redirect to login page
        } else {
            const data = await response.json();
            alert(`Signup failed: ${data.message}`);
        }
    } catch (error) {
        console.error('Signup error:', error);
        alert('An error occurred during signup.');
    }
});
