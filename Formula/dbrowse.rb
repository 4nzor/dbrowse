# Homebrew formula for dbrowse
# 
# For local installation:
#   brew install --build-from-source ./Formula/dbrowse.rb
#
# For tap installation (after creating homebrew-dbrowse repo):
#   brew tap 4nzor/dbrowse
#   brew install dbrowse

class Dbrowse < Formula
  include Language::Python::Virtualenv

  desc "Terminal-based database management utility (TUI) for multiple database types"
  homepage "https://github.com/4nzor/dbrowse"
  url "https://github.com/4nzor/dbrowse/archive/refs/tags/v0.1.12.tar.gz"
  sha256 "db603c59ee6179e82d54f5974787c57e4c12d0f780c8317bde8b4a7709aa6978"  # SHA256 for v0.1.12
  license "MIT"
  head "https://github.com/4nzor/dbrowse.git", branch: "main"

  depends_on "python@3.10"

  def install
    python3 = Formula["python@3.10"].opt_bin/"python3.10"
    system python3, "-m", "venv", libexec
    
    # Install requirements from requirements.txt
    requirements = buildpath/"requirements.txt"
    system libexec/"bin/pip", "install", "-r", requirements if requirements.exist?
    
    # Install the package itself
    system libexec/"bin/pip", "install", buildpath
    
    # Link binaries
    bin.install Dir[libexec/"bin/dbrowse*"]
  end

  test do
    # Test that the command exists and shows help
    system "#{bin}/dbrowse", "--help"
  end
end
