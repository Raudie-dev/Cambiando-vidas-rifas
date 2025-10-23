document.addEventListener("DOMContentLoaded", () => {
  console.log("[v0] Raffle app loaded successfully")

  // Header scroll effect
  const header = document.querySelector(".header")
  window.addEventListener("scroll", () => {
    if (window.scrollY > 50) {
      header.classList.add("scrolled")
    } else {
      header.classList.remove("scrolled")
    }
  })

  let lastScrollY = window.scrollY

  window.addEventListener("scroll", () => {
    const currentScrollY = window.scrollY
    const hero = document.querySelector(".hero")
    const rifasSection = document.querySelector(".rifas-section")
    const howItWorks = document.querySelector(".how-it-works")

    // Parallax and fade out for hero
    if (hero) {
      const heroHeight = hero.offsetHeight
      const scrollProgress = Math.min(currentScrollY / heroHeight, 1)

      hero.style.transform = `translateY(${currentScrollY * 0.5}px)`
      hero.style.opacity = Math.max(1 - scrollProgress * 1.5, 0)
    }

    // Fade out for rifas section when scrolling to "How It Works"
    if (rifasSection && howItWorks) {
      const rifasBottom = rifasSection.offsetTop + rifasSection.offsetHeight
      const fadeStart = rifasBottom - window.innerHeight / 2

      if (currentScrollY > fadeStart) {
        const fadeProgress = Math.min((currentScrollY - fadeStart) / (window.innerHeight / 2), 1)
        rifasSection.style.opacity = Math.max(1 - fadeProgress, 0)
        rifasSection.style.transform = `translateY(-${fadeProgress * 50}px)`
      } else {
        rifasSection.style.opacity = 1
        rifasSection.style.transform = "translateY(0)"
      }
    }

    lastScrollY = currentScrollY
  })

  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -100px 0px",
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1"
        entry.target.style.transform = "translateY(0)"
        observer.unobserve(entry.target)
      }
    })
  }, observerOptions)

  // Observe sections for animation
  document.querySelectorAll(".section-header").forEach((el) => {
    el.style.opacity = "0"
    el.style.transform = "translateY(30px)"
    el.style.transition = "opacity 0.8s ease, transform 0.8s ease"
    observer.observe(el)
  })

  const animateCounter = (element, target) => {
    let current = 0
    const increment = target / 50
    const timer = setInterval(() => {
      current += increment
      if (current >= target) {
        element.textContent = target.toLocaleString()
        clearInterval(timer)
      } else {
        element.textContent = Math.floor(current).toLocaleString()
      }
    }, 30)
  }

  // Animate statistics when visible
  const statsObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const statNumbers = entry.target.querySelectorAll(".stat-number, .about-stat-number")
          statNumbers.forEach((stat) => {
            const text = stat.textContent
            const number = Number.parseInt(text.replace(/[^0-9]/g, ""))
            if (!isNaN(number)) {
              stat.textContent = "0"
              setTimeout(() => {
                animateCounter(stat, number)
              }, 200)
            }
          })
          statsObserver.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.5 },
  )

  const heroStats = document.querySelector(".hero-stats")
  if (heroStats) {
    statsObserver.observe(heroStats)
  }

  const aboutStats = document.querySelector(".about-stats")
  if (aboutStats) {
    statsObserver.observe(aboutStats)
  }

  // Mobile Menu Toggle
  const menuToggle = document.querySelector(".mobile-menu-btn")
  const navMenu = document.querySelector(".nav-menu")

  if (menuToggle && navMenu) {
    menuToggle.addEventListener("click", function () {
      this.classList.toggle("active")
      navMenu.classList.toggle("active")
    })

    // Close menu when clicking on a nav link
    const navLinks = document.querySelectorAll(".nav-menu a")
    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        menuToggle.classList.remove("active")
        navMenu.classList.remove("active")
      })
    })

    // Close menu when clicking outside
    document.addEventListener("click", (event) => {
      const isClickInsideNav = navMenu.contains(event.target)
      const isClickOnToggle = menuToggle.contains(event.target)

      if (navMenu.classList.contains("active") && !isClickInsideNav && !isClickOnToggle) {
        menuToggle.classList.remove("active")
        navMenu.classList.remove("active")
      }
    })
  }

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault()

      const targetId = this.getAttribute("href")
      const targetElement = document.querySelector(targetId)

      if (targetElement) {
        const headerHeight = document.querySelector(".header").offsetHeight
        const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - headerHeight

        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        })
      }
    })
  })

  // Auto-rotation for prizes carousel on purchase page
  const prizesCarousel = document.querySelector(".prizes-carousel")
  if (prizesCarousel) {
    let prizeAutoRotate = setInterval(() => {
      const items = prizesCarousel.querySelectorAll(".carousel-item")
      if (items.length <= 1) return

      let currentIndex = Array.from(items).findIndex((item) => item.classList.contains("active"))
      if (currentIndex < 0) currentIndex = 0

      items[currentIndex].classList.remove("active")
      currentIndex = (currentIndex + 1) % items.length
      items[currentIndex].classList.add("active")

      const indicators = prizesCarousel.querySelectorAll(".indicator")
      if (indicators.length) {
        indicators.forEach((ind) => ind.classList.remove("active"))
        if (indicators[currentIndex]) indicators[currentIndex].classList.add("active")
      }
    }, 5000) // Change every 5 seconds

    // Stop auto-rotation on hover
    prizesCarousel.addEventListener("mouseenter", () => {
      clearInterval(prizeAutoRotate)
    })

    prizesCarousel.addEventListener("mouseleave", () => {
      prizeAutoRotate = setInterval(() => {
        const items = prizesCarousel.querySelectorAll(".carousel-item")
        if (items.length <= 1) return

        let currentIndex = Array.from(items).findIndex((item) => item.classList.contains("active"))
        if (currentIndex < 0) currentIndex = 0

        items[currentIndex].classList.remove("active")
        currentIndex = (currentIndex + 1) % items.length
        items[currentIndex].classList.add("active")

        const indicators = prizesCarousel.querySelectorAll(".indicator")
        if (indicators.length) {
          indicators.forEach((ind) => ind.classList.remove("active"))
          if (indicators[currentIndex]) indicators[currentIndex].classList.add("active")
        }
      }, 5000)
    })
  }

  function openRaffleModal(rifaId) {
    const card = document.querySelector(`.rifa-card[data-card-id="${rifaId}"]`)
    if (!card) return

    const modal = document.getElementById("raffleDetailModal")
    if (!modal) return

    // Extract data from card
    const data = card.querySelector(".rifa-data")
    if (!data) return

    const titulo = data.querySelector(".data-titulo")?.textContent || ""
    const descripcion = data.querySelector(".data-descripcion")?.textContent || ""
    const precio = data.querySelector(".data-precio")?.textContent || "0.00"
    const fecha = data.querySelector(".data-fecha")?.textContent || ""
    const ticketsSold = data.querySelector(".data-tickets-sold")?.textContent || "0"
    const totalTickets = data.querySelector(".data-total-tickets")?.textContent || "0"
    const ticketsAvailable = data.querySelector(".data-tickets-available")?.textContent || "0"
    const progress = data.querySelector(".data-progress")?.textContent || "0"
    const url = data.querySelector(".data-url")?.textContent || "#"

    // Get images
    const imagesContainer = data.querySelector(".data-images")
    const imageUrls = imagesContainer
      ? Array.from(imagesContainer.querySelectorAll(".data-image-url")).map((el) => el.textContent)
      : []

    // Populate modal
    document.getElementById("raffleModalTitle").textContent = titulo
    document.getElementById("raffleModalPrice").textContent = `Bs. ${precio}`
    document.getElementById("raffleModalDate").textContent = fecha
    document.getElementById("raffleModalTickets").textContent = `${ticketsSold}/${totalTickets}`
    document.getElementById("raffleModalAvailable").textContent = `${ticketsAvailable} tickets disponibles`
    document.getElementById("raffleModalDescription").textContent = descripcion
    document.getElementById("raffleModalProgressBar").style.width = `${progress}%`
    document.getElementById("raffleModalBuyBtn").href = url

    // Populate carousel
    const carouselWrapper = document.getElementById("raffleModalCarouselWrapper")
    const indicatorsContainer = document.getElementById("modalCarouselIndicators")
    const prevBtn = document.getElementById("modalPrevBtn")
    const nextBtn = document.getElementById("modalNextBtn")

    carouselWrapper.innerHTML = ""
    indicatorsContainer.innerHTML = ""

    if (imageUrls.length > 0) {
      imageUrls.forEach((url, index) => {
        const img = document.createElement("img")
        img.src = url
        img.alt = `${titulo} - Premio ${index + 1}`
        img.className = `rifa-image ${index === 0 ? "active" : ""}`
        carouselWrapper.appendChild(img)

        const indicator = document.createElement("span")
        indicator.className = `indicator ${index === 0 ? "active" : ""}`
        indicator.onclick = () => goToModalSlide(index)
        indicatorsContainer.appendChild(indicator)
      })

      // Show/hide navigation buttons
      if (imageUrls.length > 1) {
        prevBtn.style.display = "flex"
        nextBtn.style.display = "flex"
      } else {
        prevBtn.style.display = "none"
        nextBtn.style.display = "none"
      }
    } else {
      // No images, show placeholder
      const placeholder = document.createElement("div")
      placeholder.className = "rifa-image-placeholder active"
      placeholder.innerHTML = '<i class="fas fa-gift" style="font-size: 4rem; color: white;"></i>'
      placeholder.style.display = "flex"
      placeholder.style.alignItems = "center"
      placeholder.style.justifyContent = "center"
      placeholder.style.width = "100%"
      placeholder.style.height = "100%"
      carouselWrapper.appendChild(placeholder)

      prevBtn.style.display = "none"
      nextBtn.style.display = "none"
    }

    // Show modal
    modal.style.display = "flex"
    document.body.style.overflow = "hidden"
  }

  function closeRaffleModal() {
    const modal = document.getElementById("raffleDetailModal")
    if (modal) {
      modal.style.display = "none"
      document.body.style.overflow = "auto"
    }
  }

  function changeModalSlide(direction) {
    const carousel = document.getElementById("raffleModalCarouselWrapper")
    if (!carousel) return

    const images = carousel.querySelectorAll(".rifa-image")
    const indicators = document.querySelectorAll("#modalCarouselIndicators .indicator")

    if (images.length === 0) return

    let currentIndex = Array.from(images).findIndex((img) => img.classList.contains("active"))
    if (currentIndex < 0) currentIndex = 0

    images[currentIndex].classList.remove("active")
    if (indicators[currentIndex]) indicators[currentIndex].classList.remove("active")

    currentIndex = (currentIndex + direction + images.length) % images.length

    images[currentIndex].classList.add("active")
    if (indicators[currentIndex]) indicators[currentIndex].classList.add("active")
  }

  function goToModalSlide(index) {
    const carousel = document.getElementById("raffleModalCarouselWrapper")
    if (!carousel) return

    const images = carousel.querySelectorAll(".rifa-image")
    const indicators = document.querySelectorAll("#modalCarouselIndicators .indicator")

    if (index < 0 || index >= images.length) return

    images.forEach((img) => img.classList.remove("active"))
    indicators.forEach((ind) => ind.classList.remove("active"))

    images[index].classList.add("active")
    if (indicators[index]) indicators[index].classList.add("active")
  }

  console.log("[v0] Scroll animations initialized")
})
