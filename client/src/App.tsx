import { useState } from 'react';
import Library from './components/Library/Library';
import Reader from './components/Reader/Reader';

export default function App() {
  const [activeBookId, setActiveBookId] = useState<string | null>(null);

  if (activeBookId) {
    return <Reader bookId={activeBookId} onBack={() => setActiveBookId(null)} />;
  }

  return <Library onSelectBook={setActiveBookId} />;
}
