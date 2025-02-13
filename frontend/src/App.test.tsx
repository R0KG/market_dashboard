import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

describe('App Component', () => {
  test('renders sentiment analysis form', () => {
    render(<App />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
}); 
