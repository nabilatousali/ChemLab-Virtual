import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
    return (
        <nav className="navbar">
            <div className="navbar-logo">
                <h1>ChemLab</h1>
            </div>
            <ul className="navbar-links">
                <li>
                    <Link to="/" className="navbar-link">Home</Link>
                </li>
                <li>
                    <Link to="/experiments" className="navbar-link">Experiments</Link>
                </li>
                <li>
                    <Link to="/resources" className="navbar-link">Resources</Link>
                </li>
                <li>
                    <Link to="/about" className="navbar-link">About</Link>
                </li>
            </ul>
        </nav>
    );
};

export default Navbar;