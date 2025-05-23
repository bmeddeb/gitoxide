use crate::Time;

/// Access
impl Time {
    /// Return true if this time has been initialized to anything non-default, i.e. 0.
    pub fn is_set(&self) -> bool {
        *self != Self::default()
    }
}

/// Various ways to describe a time format.
#[derive(Debug, Clone, Copy)]
pub enum Format {
    /// A custom format limited to what's in the [`format`](mod@format) submodule.
    Custom(CustomFormat),
    /// The seconds since 1970, also known as unix epoch, like `1660874655`.
    Unix,
    /// The seconds since 1970, followed by the offset, like `1660874655 +0800`
    Raw,
}

/// A custom format for printing and parsing time.
#[derive(Clone, Copy, Debug)]
pub struct CustomFormat(pub(crate) &'static str);

impl CustomFormat {
    /// Create a new custom `format` suitable for use with the [`jiff`] crate.
    pub const fn new(format: &'static str) -> Self {
        Self(format)
    }
}

impl From<CustomFormat> for Format {
    fn from(custom_format: CustomFormat) -> Format {
        Format::Custom(custom_format)
    }
}

///
pub mod format;
mod init;
mod write;
