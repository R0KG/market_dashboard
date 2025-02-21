import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters long');
            return;
        }

        try {
            setIsLoading(true);
            setError('');

            await axios.post('http://localhost:8000/register', {
                email,
                password
            });

            setIsLoading(false);
            navigate('/login');
        } catch (err) {
            setIsLoading(false);
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || 'Registration failed');
            } else {
                setError('An unexpected error occurred');
            }
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-box">
                <h2>Create Account</h2>
                
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            required
                            disabled={isLoading}
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            required
                            disabled={isLoading}
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">Confirm Password</label>
                        <input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Confirm your password"
                            required
                            disabled={isLoading}
                        />
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    <button 
                        type="submit" 
                        className="submit-button"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Creating Account...' : 'Register'}
                    </button>
                </form>

                <div className="auth-footer">
                    Already have an account?{' '}
                    <a href="/login" className="auth-link">
                        Login here
                    </a>
                </div>
            </div>
        </div>
    );
}