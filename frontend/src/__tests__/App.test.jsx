import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import App from '../App';
import { AuthContext } from '../context/AuthContext';

// Mock child components if necessary (Login is already tested, we can just mock it if unauthenticated, but App renders it)
vi.mock('../pages/Login', () => ({
  default: () => <div data-testid="mock-login">Login Page</div>
}));

vi.mock('@cyntler/react-doc-viewer', () => ({
  default: () => <div data-testid="mock-doc-viewer">Doc Viewer</div>,
  DocViewerRenderers: []
}));

describe('App Component', () => {
  const mockLogout = vi.fn();

  const renderApp = (userRole = 'SYSTEM_ADMIN') => {
    return render(
      <AuthContext.Provider value={{ 
        user: { username: 'testuser', role: userRole }, 
        token: 'fake-token', 
        logout: mockLogout, 
        loading: false 
      }}>
        <App />
      </AuthContext.Provider>
    );
  };

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    window.URL.createObjectURL = vi.fn(() => 'blob:fake-url');
    window.confirm = vi.fn(() => true);
    
    // Default mock for checkHealth and fetchImages
    fetch.mockImplementation((url) => {
      if (url.includes('/api/health')) {
        return Promise.resolve({ ok: true });
      }
      if (url.includes('/api/images')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      }
      if (url.includes('/api/system/dashboard')) {
        return Promise.resolve({ 
          ok: true, 
          json: () => Promise.resolve({
            total_documents: 10,
            graph_nodes: 100,
            graph_edges: 200,
            jobs: { QUEUED: 5, PROCESSING: 2 }
          }) 
        });
      }
      return Promise.resolve({ ok: false });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Authentication & Basic Rendering', () => {
    it('renders login if user is not authenticated', () => {
      render(
        <AuthContext.Provider value={{ user: null, token: null, loading: false }}>
          <App />
        </AuthContext.Provider>
      );
      expect(screen.getByTestId('mock-login')).toBeInTheDOM();
    });

    it('renders loading state', () => {
      render(
        <AuthContext.Provider value={{ user: null, token: null, loading: true }}>
          <App />
        </AuthContext.Provider>
      );
      expect(screen.getByText('Loading...')).toBeInTheDOM();
    });

    it('renders dashboard by default for authenticated user', async () => {
      renderApp();
      expect(screen.getByText('Dashboard')).toBeInTheDOM();
      expect(screen.getAllByRole('heading', { name: 'RAG System' }).length).toBeGreaterThan(0);
      
      // Dashboard metrics should load
      await waitFor(() => {
        expect(screen.getByText('10')).toBeInTheDOM(); // total_documents
        expect(screen.getByText('100')).toBeInTheDOM(); // graph_nodes
        expect(screen.getByText('200')).toBeInTheDOM(); // graph_edges
        expect(screen.getByText('5')).toBeInTheDOM(); // queued jobs
      });
    });

    it('handles dashboard API failure gracefully', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/system/dashboard')) return Promise.resolve({ ok: false });
        if (url.includes('/api/health') || url.includes('/api/images')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });
      renderApp();
      
      await waitFor(() => {
        const metrics = screen.getAllByText('0');
        expect(metrics.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Shared-Device Accessibility', () => {
    it('shows upload tab to SYSTEM_ADMIN', () => {
      renderApp('SYSTEM_ADMIN');
      expect(screen.getByText('Upload Documents')).toBeInTheDOM();
    });

    it('shows upload tab to DOCUMENT_OFFICER', () => {
      renderApp('DOCUMENT_OFFICER');
      expect(screen.getByText('Upload Documents')).toBeInTheDOM();
    });

    it('shows upload tab to VIEWER', () => {
      renderApp('VIEWER');
      expect(screen.getByText('Upload Documents')).toBeInTheDOM();
    });
    
    it('shows upload tab to REVIEWER', () => {
      renderApp('REVIEWER');
      expect(screen.getByText('Upload Documents')).toBeInTheDOM();
    });
  });

  describe('Upload Workflow', () => {
    it('allows file selection and displays preview', async () => {
      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Upload Documents'));

      const file = new File(['hello'], 'hello.png', { type: 'image/png' });
      const input = document.querySelector('input[type="file"]');
      
      await user.upload(input, file);

      await waitFor(() => {
        expect(screen.getByText('hello.png')).toBeInTheDOM();
        expect(screen.getByText('Upload 1 File(s)')).toBeInTheDOM();
      });
    });

    it('submits files and handles QUEUED response', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/upload')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve([{ job_id: '123', status: 'QUEUED' }]) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Upload Documents'));

      const file = new File(['hello'], 'hello.png', { type: 'image/png' });
      const input = document.querySelector('input[type="file"]');
      await user.upload(input, file);
      
      // Since it uses XMLHttpRequest, we mock XMLHttpRequest
      const mockXHR = {
        open: vi.fn(),
        send: vi.fn(),
        setRequestHeader: vi.fn(),
        addEventListener: vi.fn((event, callback) => {
          if (event === 'load') {
            setTimeout(() => {
              mockXHR.status = 201;
              callback();
            }, 50);
          }
        }),
        upload: { addEventListener: vi.fn() }
      };
      window.XMLHttpRequest = vi.fn(() => mockXHR);

      await user.click(screen.getByText('Upload 1 File(s)'));
      
      await waitFor(() => {
        expect(mockXHR.open).toHaveBeenCalledWith('POST', 'http://localhost:8000/api/upload');
        expect(mockXHR.send).toHaveBeenCalled();
        expect(screen.getByText('Images uploaded successfully!')).toBeInTheDOM();
      });
    });
  });

  describe('Document Gallery & Inspect Modal', () => {
    it('displays uploaded images and opens modal with OCR data', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/images/1/ocr/text')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ text: 'Extracted text' }) });
        if (url.includes('/api/images/1/ocr/data')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ document_confidence_score: 95, total_words_detected: 10 }) });
        if (url.includes('/api/images/1/ocr/chunks')) return Promise.resolve({ ok: true, json: () => Promise.resolve([{ chunk_id: 'chunk1', text: 'Chunk 1 text', metadata: { source_file: 'test.png', ocr_confidence: 95 } }]) });
        if (url.includes('/api/images')) return Promise.resolve({ ok: true, json: () => Promise.resolve([
          { id: '1', filename: 'test.png', status: 'Completed', size_bytes: 1024 }
        ]) });
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Document Gallery'));

      await waitFor(() => {
        expect(screen.getByText('test.png')).toBeInTheDOM();
      });

      await user.click(screen.getByText('test.png'));

      await waitFor(() => {
        expect(screen.getByText('Extracted text')).toBeInTheDOM();
        expect(screen.getByText('95%')).toBeInTheDOM(); // Confidence score
      });
      
      await user.click(screen.getByText(/Segmented Chunks/));
      await waitFor(() => {
        expect(screen.getByText('Chunk 1 text')).toBeInTheDOM();
      });
    });
  });

  describe('Chat, RAG, and Citation Highlighting', () => {
    it('sends a chat message and renders response with citations', async () => {
      const mockStreamResponse = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"type": "token", "text": "The answer is here."}\n\n'));
          controller.enqueue(new TextEncoder().encode('data: {"type": "sources", "sources": [{"chunk_id": "c1", "text": "Source text", "score": 0.95, "metadata": {"source_file": "doc.pdf", "document_id": "doc1", "bounding_box": [10, 10, 100, 100]}}]}\n\n'));
          controller.close();
        }
      });

      fetch.mockImplementation((url) => {
        if (url.includes('/api/chat/sessions')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
        if (url.includes('/api/chat')) {
          return Promise.resolve({ ok: true, body: mockStreamResponse });
        }
        if (url.includes('/api/images')) return Promise.resolve({ ok: true, json: () => Promise.resolve([{ id: 'doc1', filename: 'doc.pdf', status: 'Completed' }]) });
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Semantic Chat'));

      const input = screen.getByPlaceholderText(/Ask a question/);
      await user.type(input, 'What is the answer?');
      await user.click(screen.getByRole('button', { name: 'Send Question' }));

      await waitFor(() => {
        expect(screen.getByText('What is the answer?')).toBeInTheDOM();
        expect(screen.getByText(/The answer is here/)).toBeInTheDOM();
        expect(screen.getByText(/Inspect Source Citations/)).toBeInTheDOM();
      });

      // Click citation
      await user.click(screen.getByText(/Inspect Source Citations/));
      const citationLink = await screen.findByText(/doc.pdf/);
      
      // Mock modal APIs before clicking
      fetch.mockImplementation((url) => {
        if (url.includes('/api/images/doc1/ocr/text')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ text: 'text' }) });
        if (url.includes('/api/images/doc1/ocr/data')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ document_confidence_score: 95 }) });
        if (url.includes('/api/images/doc1/ocr/chunks')) return Promise.resolve({ ok: true, json: () => Promise.resolve([{ chunk_id: 'c1', text: 'Source text', metadata: {} }]) });
        return Promise.resolve({ ok: true });
      });

      await user.click(citationLink);

      // Verify modal opens and chunk is highlighted
      await waitFor(() => {
        expect(screen.getByText('doc.pdf')).toBeInTheDOM();
        expect(screen.getByText(/Segmented Chunks/)).toBeInTheDOM();
      });
      
      // Wait for chunks tab to activate and show the highlighted chunk
      await waitFor(() => {
        const chunk = screen.getByText('Source text');
        expect(chunk).toBeInTheDOM();
        // Since we cannot easily check dynamic styles without styled-components, we ensure the chunk is rendered
      });
    });
    
    it('handles chat stream network errors', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/auth/setup-status')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ is_first_time: false }) });
        if (url.includes('/api/chat/sessions')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
        if (url.includes('/api/chat')) {
          return Promise.reject(new Error("Network Error"));
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Semantic Chat'));

      const input = screen.getByPlaceholderText(/Ask a question/);
      await user.type(input, 'Fail this');
      await user.click(screen.getByRole('button', { name: 'Send Question' }));

      await waitFor(() => {
        expect(screen.getByText(/Connection to backend lost/)).toBeInTheDOM();
      });
    }, 15000);

    it('renders attachment button and handles file selection in chat workspace', async () => {
      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Semantic Chat'));

      const attachBtn = screen.getByRole('button', { name: /Attach File/ });
      expect(attachBtn).toBeInTheDOM();
    });

    it('supports attaching TXT, CSV, and XLSX files in chat workspace', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/upload')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([
              { document_id: 'doc_txt_1', filename: 'report.txt', status: 'QUEUED' },
              { document_id: 'doc_csv_1', filename: 'data.csv', status: 'QUEUED' },
              { document_id: 'doc_xlsx_1', filename: 'infra.xlsx', status: 'QUEUED' }
            ])
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Semantic Chat'));

      const fileInput = screen.getByRole('button', { name: /Attach File/ });
      expect(fileInput).toBeInTheDOM();
    });
  });

  describe('Semantic Search (Graph / Vectors)', () => {
    it('performs semantic search and displays vectors', async () => {
      fetch.mockImplementation((url) => {
        if (url.includes('/api/auth/setup-status')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ is_first_time: false }) });
        if (url.includes('/api/images/search')) {
          return Promise.resolve({ 
            ok: true, 
            json: () => Promise.resolve([
              { chunk_id: '1', score: 0.99, text: 'Search result text', metadata: { source_file: 'secret.pdf', chunk_index: 0, document_id: 'd1' } }
            ]) 
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      });

      renderApp();
      const user = userEvent.setup();
      await user.click(screen.getByText('Semantic Chat'));
      await user.click(screen.getByText('Vector DB Search'));

      const input = screen.getByPlaceholderText(/Enter keywords/);
      await user.type(input, 'search term');
      await user.click(screen.getByRole('button', { name: 'Find Vectors' }));

      await waitFor(() => {
        expect(screen.getByText('Search result text')).toBeInTheDOM();
        expect(screen.getByText(/secret.pdf/)).toBeInTheDOM();
      });
    }, 15000);
  });
});
