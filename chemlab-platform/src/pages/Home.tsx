import React from 'react';
import Navbar from '../components/Navbar';

const Home: React.FC = () => {
    return (
        <div className="home-container">
            <Navbar />
            <header className="home-header">
                <h1>Welcome to ChemLab</h1>
                <p>Your virtual chemistry laboratory awaits!</p>
            </header>
            <main className="home-main">
                <section className="home-intro">
                    <h2>Explore Chemistry</h2>
                    <p>Engage in interactive experiments and learn about chemical reactions in a safe environment.</p>
                </section>
                <section className="home-features">
                    <h2>Features</h2>
                    <ul>
                        <li>Real-time simulations</li>
                        <li>Comprehensive tutorials</li>
                        <li>Collaborative projects</li>
                    </ul>
                </section>
            </main>
            <footer className="home-footer">
                <p>&copy; 2023 ChemLab. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default Home;