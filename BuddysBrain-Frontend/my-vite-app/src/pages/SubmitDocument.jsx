import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { apiBaseUrl, serviceError, LIVE_TIMEOUT_MS } from '../lib/liveService';
import "../styles/SubmitDocument.css";
import "../styles/Demo.css";
import axios from 'axios';
import SubmittedPage from './SubmittedPage';

const SubmitDocumentPage = () => {
  const [mediaType, setMediaType] = useState('');
  const [description, setDescription] = useState('');
  const [courseName, setCourseName] = useState('');
  const [title, setTitle] = useState('');
  const [uploadLink, setUploadLink] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const busy = useRef(false);
  const API_BASE_URL = apiBaseUrl();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy.current || !API_BASE_URL) return;

    if (!mediaType || !description || !courseName || !title) {
      setError('Please fill out all fields.');
      return;
    }

    if ((mediaType === 'article' || mediaType === 'video') && !uploadLink) {
      setError('Please provide a link.');
      return;
    }

    if ((mediaType === 'document' || mediaType === 'image') && !uploadFile) {
      setError('Please upload a file.');
      return;
    }

    setError('');
    busy.current = true;
    setSubmitting(true);

    try {
      if (mediaType === 'article' || mediaType === 'video') {
        const payload = {
          title,
          description,
          media_type: mediaType,
          media_link: uploadLink,
          course: courseName,
          summary: description
        };
        await axios.post(`${API_BASE_URL}/resources`, payload, { timeout: LIVE_TIMEOUT_MS });
        
      } else {
        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('title', title);
        formData.append('description', description);
        formData.append('course', courseName);
        formData.append('summary', description);

        await axios.post(`${API_BASE_URL}/upload`, formData, {
          timeout: LIVE_TIMEOUT_MS,
        });
      }

      setSubmitted(true);
    } catch (err) {
      setError(serviceError(err));
    } finally {
      busy.current = false;
      setSubmitting(false);
    }
  };

  const handleFileChange = (e) => {
    setUploadFile(e.target.files[0]);
  };

  if (!API_BASE_URL) return (
    <main className="study-page">
      <Link to="/" className="study-back">← Home</Link>
      <h1>Uploads are not enabled yet</h1>
      <p>You can explore the sample lessons now. Uploads will be available once the live service is connected.</p>
      <Link to="/ask">Explore demo</Link>
    </main>
  );

  return (
    <div className="page-container">
      <a href="/" className="back-button">Back</a>

      {submitted ? (
        <SubmittedPage title={title} />
      ) : (
        <div className="content">
          <h1>Help Buddy Help You!</h1>
          <form onSubmit={handleSubmit} className="form-container">
            {error && <p className="error" role="alert">{error}</p>}
            <fieldset disabled={submitting} className="submission-fields">

            {/* Title */}
            <div className="form-group-row">
              <label htmlFor="title">Title:</label>
              <input
                type="text"
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="E.g. Heaps"
              />
            </div>

            {/* Media Type */}
            <div className="form-group-row">
              <label htmlFor="mediaType">Media Type:</label>
              <select
                id="mediaType"
                value={mediaType}
                onChange={(e) => {
                  setMediaType(e.target.value);
                  setUploadLink('');
                  setUploadFile(null);
                }}
              >
                <option value="" disabled>Select type</option>
                <option value="article">Article</option>
                <option value="video">YouTube Video</option>
                <option value="document">Document</option>
                <option value="image">Image</option>
              </select>
            </div>

            {/* Upload Field for Link */}
            {(mediaType === 'article' || mediaType === 'video') && (
              <div className="form-group-row">
                <label htmlFor="uploadLink">
                  {mediaType === 'article' ? 'Article URL:' : 'YouTube URL:'}
                </label>
                <input
                  type="text"
                  id="uploadLink"
                  placeholder={
                    mediaType === 'article'
                      ? 'E.g. https://towardsdatascience.com/...'
                      : 'E.g. https://www.youtube.com/watch?v=...'
                  }
                  
                  value={uploadLink}
                  onChange={(e) => setUploadLink(e.target.value)}
                />
              </div>
            )}

            {/* Upload Field for File */}
            {(mediaType === 'document' || mediaType === 'image') && (
              <div className="form-group-row">
                <label htmlFor="uploadFile">
                  {mediaType === 'document' ? 'Document:' : 'Image:'}
                </label>
                <input
                  type="file"
                  id="uploadFile"
                  accept={mediaType === 'document' ? ".pdf,.docx,.txt" : ".png,.jpg,.jpeg,.webp,.gif"}
                  onChange={handleFileChange}
                />
                {uploadFile && <p className="file-info">Selected: {uploadFile.name}</p>}
              </div>
            )}

            {/* Course */}
            <div className="form-group-row">
              <label htmlFor="courseName">Course Name:</label>
              <input
                type="text"
                id="courseName"
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                placeholder="E.g. Intro to Computer Science"
              />
            </div>

            {/* Description */}
            <div className="form-group-row">
              <label htmlFor="description">Description:</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="E.g. This PDF gives a clear explanation of heaps..."
                rows={4}
              />
            </div>

            <button type="submit">{submitting ? 'Submitting...' : 'Submit'}</button>
            </fieldset>
          </form>
        </div>
      )}
    </div>
  );
};

export default SubmitDocumentPage;
