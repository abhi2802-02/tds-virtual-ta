import React, { useState } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      const data = await response.json();
      setAnswer(data);
    } catch (error) {
      console.error('Error:', error);
      setAnswer({
        answer: 'Error: Could not get response from API.',
        links: []
      });
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/status`);
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const sampleQuestions = [
    "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?",
    "What Python libraries are covered in the TDS course?",
    "How do I handle machine learning models in assignments?",
    "What are the key topics in Tools in Data Science?"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            TDS Virtual Teaching Assistant
          </h1>
          <p className="text-lg text-gray-600">
            Ask questions about Tools in Data Science course content and forum discussions
          </p>
          <div className="mt-4">
            <button
              onClick={checkStatus}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition duration-200"
            >
              Check API Status
            </button>
          </div>
          
          {status && (
            <div className="mt-4 p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-semibold text-gray-800 mb-2">API Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium">Status:</span>
                  <span className={`ml-2 px-2 py-1 rounded ${
                    status.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {status.status}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Data Loaded:</span>
                  <span className={`ml-2 ${status.data_loaded ? 'text-green-600' : 'text-red-600'}`}>
                    {status.data_loaded ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Documents:</span>
                  <span className="ml-2 text-blue-600">{status.total_documents}</span>
                </div>
                <div>
                  <span className="font-medium">OpenAI:</span>
                  <span className={`ml-2 ${status.openai_configured ? 'text-green-600' : 'text-red-600'}`}>
                    {status.openai_configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sample Questions */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Try these sample questions:</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sampleQuestions.map((sampleQuestion, index) => (
              <button
                key={index}
                onClick={() => setQuestion(sampleQuestion)}
                className="text-left p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition duration-200 border border-gray-200 hover:border-blue-300"
              >
                <span className="text-sm text-blue-600">"{sampleQuestion}"</span>
              </button>
            ))}
          </div>
        </div>

        {/* Question Form */}
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="mb-8">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
                Ask your question about TDS:
              </label>
              <textarea
                id="question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={4}
                required
              />
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="mt-4 w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition duration-200 font-medium"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Getting Answer...
                  </div>
                ) : (
                  'Ask Question'
                )}
              </button>
            </div>
          </form>

          {/* Answer Display */}
          {answer && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Answer:</h2>
              <div className="prose max-w-none">
                <p className="text-gray-700 mb-6 leading-relaxed whitespace-pre-wrap">
                  {answer.answer}
                </p>
              </div>

              {answer.links && answer.links.length > 0 && (
                <div className="border-t pt-4">
                  <h3 className="text-lg font-medium text-gray-800 mb-3">Relevant Links:</h3>
                  <div className="space-y-2">
                    {answer.links.map((link, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        <span className="text-blue-600 font-medium text-sm mt-1">{index + 1}.</span>
                        <a
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 hover:underline flex-1"
                        >
                          <div className="font-medium">{link.text}</div>
                          <div className="text-sm text-gray-500 break-all">{link.url}</div>
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* API Information */}
        <div className="mt-12 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">API Information</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium text-gray-700">Endpoint URL:</h3>
                <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                  {backendUrl}/api/
                </code>
              </div>
              <div>
                <h3 className="font-medium text-gray-700">Sample cURL command:</h3>
                <pre className="text-sm bg-gray-100 p-3 rounded overflow-x-auto">
{`curl "${backendUrl}/api/" \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?"}'`}
                </pre>
              </div>
              <div>
                <h3 className="font-medium text-gray-700">Response Format:</h3>
                <pre className="text-sm bg-gray-100 p-3 rounded overflow-x-auto">
{`{
  "answer": "Based on the course materials...",
  "links": [
    {
      "url": "https://discourse.onlinedegree.iitm.ac.in/t/...",
      "text": "Discussion title or content preview"
    }
  ]
}`}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Virtual Teaching Assistant for Tools in Data Science (TDS) - IIT Madras</p>
          <p className="mt-1">Built with React, FastAPI, ChromaDB, and OpenAI</p>
        </div>
      </div>
    </div>
  );
}

export default App;
