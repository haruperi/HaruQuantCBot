/**
 * @file mmap_reader.hpp
 * @brief Cross-platform memory-mapped file reader
 *
 * Provides zero-copy access to binary files via memory mapping.
 * Supports both Windows and Linux platforms.
 */

#pragma once

#include <string>
#include <cstdint>
#include <stdexcept>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#endif

namespace hqt {

/**
 * @brief Exception for mmap errors
 */
class MmapError : public std::runtime_error {
public:
    explicit MmapError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief Cross-platform memory-mapped file reader
 *
 * Provides read-only access to files via memory mapping for zero-copy I/O.
 * Automatically handles platform differences (Windows vs POSIX).
 *
 * Example:
 * @code
 * MmapReader reader("data.bin");
 * const uint8_t* data = reader.data();
 * size_t size = reader.size();
 * @endcode
 */
class MmapReader {
private:
#ifdef _WIN32
    HANDLE file_handle_;
    HANDLE map_handle_;
#else
    int file_descriptor_;
#endif
    void* mapped_ptr_;
    size_t file_size_;
    std::string file_path_;

public:
    /**
     * @brief Construct and open memory-mapped file
     * @param path Path to file
     * @throws MmapError if file cannot be opened or mapped
     */
    explicit MmapReader(const std::string& path)
        :
#ifdef _WIN32
          file_handle_(INVALID_HANDLE_VALUE),
          map_handle_(nullptr),
#else
          file_descriptor_(-1),
#endif
          mapped_ptr_(nullptr),
          file_size_(0),
          file_path_(path) {
        open(path);
    }

    /**
     * @brief Destructor - closes file and unmaps memory
     */
    ~MmapReader() noexcept {
        close();
    }

    // Disable copy
    MmapReader(const MmapReader&) = delete;
    MmapReader& operator=(const MmapReader&) = delete;

    // Enable move
    MmapReader(MmapReader&& other) noexcept
        :
#ifdef _WIN32
          file_handle_(other.file_handle_),
          map_handle_(other.map_handle_),
#else
          file_descriptor_(other.file_descriptor_),
#endif
          mapped_ptr_(other.mapped_ptr_),
          file_size_(other.file_size_),
          file_path_(std::move(other.file_path_)) {
#ifdef _WIN32
        other.file_handle_ = INVALID_HANDLE_VALUE;
        other.map_handle_ = nullptr;
#else
        other.file_descriptor_ = -1;
#endif
        other.mapped_ptr_ = nullptr;
        other.file_size_ = 0;
    }

    MmapReader& operator=(MmapReader&& other) noexcept {
        if (this != &other) {
            close();

#ifdef _WIN32
            file_handle_ = other.file_handle_;
            map_handle_ = other.map_handle_;
            other.file_handle_ = INVALID_HANDLE_VALUE;
            other.map_handle_ = nullptr;
#else
            file_descriptor_ = other.file_descriptor_;
            other.file_descriptor_ = -1;
#endif
            mapped_ptr_ = other.mapped_ptr_;
            file_size_ = other.file_size_;
            file_path_ = std::move(other.file_path_);

            other.mapped_ptr_ = nullptr;
            other.file_size_ = 0;
        }
        return *this;
    }

    /**
     * @brief Get pointer to mapped memory
     * @return Const pointer to file data
     */
    const uint8_t* data() const noexcept {
        return static_cast<const uint8_t*>(mapped_ptr_);
    }

    /**
     * @brief Get file size in bytes
     */
    size_t size() const noexcept {
        return file_size_;
    }

    /**
     * @brief Get file path
     */
    const std::string& path() const noexcept {
        return file_path_;
    }

    /**
     * @brief Check if file is mapped
     */
    bool is_open() const noexcept {
        return mapped_ptr_ != nullptr;
    }

private:
    void open(const std::string& path) {
#ifdef _WIN32
        // Windows implementation
        file_handle_ = CreateFileA(
            path.c_str(),
            GENERIC_READ,
            FILE_SHARE_READ,
            nullptr,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );

        if (file_handle_ == INVALID_HANDLE_VALUE) {
            throw MmapError("Failed to open file: " + path);
        }

        // Get file size
        LARGE_INTEGER size;
        if (!GetFileSizeEx(file_handle_, &size)) {
            CloseHandle(file_handle_);
            throw MmapError("Failed to get file size: " + path);
        }
        file_size_ = static_cast<size_t>(size.QuadPart);

        if (file_size_ == 0) {
            // Empty file - no need to map
            CloseHandle(file_handle_);
            file_handle_ = INVALID_HANDLE_VALUE;
            return;
        }

        // Create file mapping
        map_handle_ = CreateFileMappingA(
            file_handle_,
            nullptr,
            PAGE_READONLY,
            0,
            0,
            nullptr
        );

        if (map_handle_ == nullptr) {
            CloseHandle(file_handle_);
            throw MmapError("Failed to create file mapping: " + path);
        }

        // Map view of file
        mapped_ptr_ = MapViewOfFile(
            map_handle_,
            FILE_MAP_READ,
            0,
            0,
            0
        );

        if (mapped_ptr_ == nullptr) {
            CloseHandle(map_handle_);
            CloseHandle(file_handle_);
            throw MmapError("Failed to map view of file: " + path);
        }

#else
        // POSIX implementation
        file_descriptor_ = ::open(path.c_str(), O_RDONLY);
        if (file_descriptor_ < 0) {
            throw MmapError("Failed to open file: " + path);
        }

        // Get file size
        struct stat st;
        if (fstat(file_descriptor_, &st) < 0) {
            ::close(file_descriptor_);
            throw MmapError("Failed to stat file: " + path);
        }
        file_size_ = static_cast<size_t>(st.st_size);

        if (file_size_ == 0) {
            // Empty file - no need to map
            ::close(file_descriptor_);
            file_descriptor_ = -1;
            return;
        }

        // Map file
        mapped_ptr_ = mmap(nullptr, file_size_, PROT_READ, MAP_PRIVATE, file_descriptor_, 0);
        if (mapped_ptr_ == MAP_FAILED) {
            ::close(file_descriptor_);
            throw MmapError("Failed to mmap file: " + path);
        }

        // Advise kernel about access pattern
        madvise(mapped_ptr_, file_size_, MADV_SEQUENTIAL);
#endif
    }

    void close() noexcept {
        if (mapped_ptr_ != nullptr) {
#ifdef _WIN32
            UnmapViewOfFile(mapped_ptr_);
            mapped_ptr_ = nullptr;
#else
            munmap(mapped_ptr_, file_size_);
            mapped_ptr_ = nullptr;
#endif
        }

#ifdef _WIN32
        if (map_handle_ != nullptr) {
            CloseHandle(map_handle_);
            map_handle_ = nullptr;
        }
        if (file_handle_ != INVALID_HANDLE_VALUE) {
            CloseHandle(file_handle_);
            file_handle_ = INVALID_HANDLE_VALUE;
        }
#else
        if (file_descriptor_ >= 0) {
            ::close(file_descriptor_);
            file_descriptor_ = -1;
        }
#endif

        file_size_ = 0;
    }
};

} // namespace hqt
