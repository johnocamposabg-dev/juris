import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Layout/navbar';
import { ROUTES } from './routes/paths';

function App() {
  return (
    <>
      <Navbar />

      <main className="container py-4">
        <Routes>
          <Route path={ROUTES.HOME} element={<h1>Inicio</h1>} />
          <Route path={ROUTES.CONSULTS} element={<h1>Consultas</h1>} />
          <Route path={ROUTES.PROPOSALS} element={<h1>Propuestas</h1>} />
          <Route path={ROUTES.ASSIGNMENTS} element={<h1>Asignaciones</h1>} />
        </Routes>
      </main>
    </>
  );
}

export default App;
