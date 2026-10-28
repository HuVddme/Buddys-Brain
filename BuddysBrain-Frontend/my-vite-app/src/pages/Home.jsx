import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import "../styles/Home.css";
import buddyLogo from '../assets/BuddysBirthday.png';
import { apiBaseUrl } from '../lib/liveService';

const LandingPage = () => {
  const [typedText, setTypedText] = useState("")
  const fullText = "What can Buddy do for you today?"
  const speed = 100 // typing speed in ms

  useEffect(() => {
    let i = 0
    const timer = setInterval(() => {
      i++
      setTypedText(fullText.slice(0, i))
      if (i >= fullText.length) {
        clearInterval(timer)
      }
    }, speed)

    // Cleanup on unmount
    return () => clearInterval(timer)
  }, [])
  return (
    <div className="landing-container">
      <div className="content">
      <img 
          className="logo" 
          src={buddyLogo} 
          alt="Buddy's Brain Logo" 
        />
        <h1 className="animate-slide-in">Welcome to Buddy's Brain</h1>
        
        {/* Typewriter Text */}
        <h2 className="typewriter-text">{typedText}</h2>
        
        <div className="buttons-row">
        <Link className="button-link" to="/ask">
            Explore demo
          </Link>
          {apiBaseUrl() && <>
            <Link className="button-link" to="/ask?mode=live">Ask live</Link>
            <Link className="button-link" to="/submit">Share Some Wisdom</Link>
          </>}
        </div>
        <p className="landing-demo-note">Try sample lessons and saved answers. No account or API key needed for the demo.</p>
      </div>
    </div>
  )
}

export default LandingPage