import { useState } from 'react';
import Library from './components/Library/Library';
import Reader from './components/Reader/Reader';
import DemoReader from './components/Reader/DemoReader';
import { BookMeta } from './types';
import './styles/App.css';

export default function App() {
  const [currentBook, setCurrentBook] = useState<BookMeta | null>(null);

  const renderReader = () => {
    if (!currentBook) return <Library onSelectBook={setCurrentBook} />;
    if (currentBook.isDemo) {
      return <DemoReader book={currentBook} onBack={() => setCurrentBook(null)} />;
    }
    return <Reader book={currentBook} onBack={() => setCurrentBook(null)} />;
  };

  return (
    <div className="app">
      <header className="app-header">
        <button className="app-logo" onClick={() => setCurrentBook(null)}>
          <span className="logo-icon">♪</span>
          <span className="logo-text">FootNote</span>
        </button>
        {currentBook && (
          <div className="app-breadcrumb">
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-title">{currentBook.title}</span>
          </div>
        )}
      </header>

      <main className="app-main">
        {renderReader()}
      </main>
    </div>
  );
}
