use thiserror::Error;

pub type RsvpResult<T> = Result<T, RsvpError>;

#[derive(Error, Debug)]
pub enum RsvpError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Parse error: {0}")]
    Parse(String),
    
    #[error("PDF parsing error: {0}")]
    PdfError(String),
    
    #[error("EPUB parsing error: {0}")]
    EpubError(String),
    
    #[error("Invalid file format: {0}")]
    InvalidFormat(String),
    
    #[error("Encoding error: {0}")]
    Encoding(String),
    
    #[error("Unsupported feature: {0}")]
    Unsupported(String),
    
    #[error("{0}")]
    Custom(String),
}

impl RsvpError {
    pub fn custom(msg: impl Into<String>) -> Self {
        RsvpError::Custom(msg.into())
    }
    
    pub fn parse(msg: impl Into<String>) -> Self {
        RsvpError::Parse(msg.into())
    }
    
    pub fn pdf(msg: impl Into<String>) -> Self {
        RsvpError::PdfError(msg.into())
    }
    
    pub fn epub(msg: impl Into<String>) -> Self {
        RsvpError::EpubError(msg.into())
    }
    
    pub fn invalid_format(msg: impl Into<String>) -> Self {
        RsvpError::InvalidFormat(msg.into())
    }
}
