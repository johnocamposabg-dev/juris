import {Link} from 'react-router-dom';
import { NAV_ITEMS, ROUTES } from '../../routes/paths';

function Navbar() {
  return (
    <nav className="navbar navbar-expand-lg navbar-color">
        <div className="container-fluid">
            <Link className="navbar-brand" to={ROUTES.HOME}>Jur</Link>
            <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span className="navbar-toggler-icon"></span>
            </button>
        </div>
    </nav>
  );
}

export default Navbar;