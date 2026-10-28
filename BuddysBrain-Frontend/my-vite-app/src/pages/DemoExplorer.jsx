import { useState } from 'react';
import { lessons, lessonPassages } from '../demo/lessons';

export default function DemoExplorer() {
  const [lessonId, setLessonId] = useState(lessons[0].id);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const lesson = lessons.find(item => item.id === lessonId);
  const passages = lessonPassages(lesson);

  return (
    <section className="demo-explorer" aria-label="Sample lesson demo">
      <div className="mode-notice">
        <strong>Demo · saved examples</strong>
        <p>Explore three sample lessons and six prepared answers. No live AI request is made, and nothing you view here is uploaded.</p>
      </div>
      <div className="lesson-picker" aria-label="Choose a sample lesson">
        {lessons.map(item => (
          <button key={item.id} aria-pressed={item.id === lessonId} onClick={() => { setLessonId(item.id); setSelectedQuestion(null); }}>
            <span>{item.course}</span>{item.title}
          </button>
        ))}
      </div>
      <div className="demo-document">
        <div className="lesson-heading">
          <h2>{lesson.title}</h2>
          <a href={lesson.url} download={`${lesson.id}.txt`}>Download sample notes</a>
        </div>
        <details key={lesson.id}>
          <summary>Read the full sample lesson</summary>
          <div className="lesson-text">{passages.map((text, index) => <p key={index}>{text}</p>)}</div>
        </details>
        <h3>Try a sample question</h3>
        <div className="suggested-questions">
          {lesson.questions.map(item => (
            <button key={item.question} aria-pressed={selectedQuestion === item} onClick={() => setSelectedQuestion(item)}>{item.question}</button>
          ))}
        </div>
      </div>
      <div aria-live="polite" aria-atomic="true">
        {selectedQuestion ? (
          <article className="demo-answer">
            <span className="answer-label">Saved sample answer · not generated live</span>
            <h3>{selectedQuestion.question}</h3>
            <p>{selectedQuestion.answer}</p>
            <h4>Supporting passages from {lesson.course}</h4>
            {selectedQuestion.passages.map(number => (
              <figure key={number}>
                <blockquote>{passages[number - 1]}</blockquote>
                <figcaption>{lesson.title} · paragraph {number}</figcaption>
              </figure>
            ))}
          </article>
        ) : <p className="demo-hint">Choose a question to see its saved answer and the passages that support it.</p>}
      </div>
      <p className="demo-hint">These are original demonstration notes, not your uploaded library. Use Ask live for your own questions when the live service is enabled.</p>
    </section>
  );
}
