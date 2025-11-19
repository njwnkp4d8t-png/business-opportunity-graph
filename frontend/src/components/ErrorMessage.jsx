/**
 * Error Message Component
 * Displays user-friendly error messages with retry option
 */

const ErrorMessage = ({ error, onRetry }) => {
  const getErrorMessage = (error) => {
    if (!error) return 'An unknown error occurred';

    if (error.isNetworkError) {
      return 'Unable to connect to the server. Please check your connection.';
    }

    if (error.isTimeout) {
      return 'Request timed out. The server took too long to respond.';
    }

    if (error.status === 404) {
      return 'The requested resource was not found.';
    }

    if (error.status === 500) {
      return 'Server error. Please try again later.';
    }

    return error.message || 'Something went wrong. Please try again.';
  };

  return (
    <div className="error-message-container">
      <div className="error-icon">❌</div>
      <h3 className="error-title">Error</h3>
      <p className="error-text">{getErrorMessage(error)}</p>
      {error?.status && (
        <p className="error-status">Status Code: {error.status}</p>
      )}
      {onRetry && (
        <button onClick={onRetry} className="error-retry-button">
          Try Again
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;
