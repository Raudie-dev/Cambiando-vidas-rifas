from django.db import models


class Rifa(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_sorteo = models.DateField()
    total_tickets = models.PositiveIntegerField(default=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # ganador: referencia al ticket ganador (si ya fue sorteado)
    winner_ticket = models.ForeignKey('Ticket', null=True, blank=True, on_delete=models.SET_NULL, related_name='won_rifa')

    class Meta:
        ordering = ['-fecha_sorteo', 'titulo']

    def __str__(self):
        return self.titulo

    @property
    def tickets_sold(self):
        return self.tickets.count()

    @property
    def tickets_available(self):
        return max(self.total_tickets - self.tickets_sold, 0)



class RifaImage(models.Model):
    rifa = models.ForeignKey(Rifa, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='rifas/')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Imagen Rifa {self.rifa_id} - {self.id}"


class Participante(models.Model):
    # Usamos un campo de texto para permitir identificaciones con cero a la izquierda
    identificacion = models.CharField(max_length=30, primary_key=True)
    nombre = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.identificacion})"


class Ticket(models.Model):
    rifa = models.ForeignKey(Rifa, related_name='tickets', on_delete=models.CASCADE)
    participante = models.ForeignKey(Participante, related_name='tickets', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    comprado_en = models.DateTimeField(auto_now_add=True)
    # referencia a la compra que reservó/creó este ticket (puede ser null si se asignó directamente)
    compra = models.ForeignKey('Compra', related_name='tickets_assigned', on_delete=models.SET_NULL, null=True, blank=True)
    # si es True el ticket está confirmado (pago verificado). Si False, está reservado por una compra pendiente.
    confirmed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('rifa', 'number')
        ordering = ['rifa', 'number']

    def __str__(self):
        return f"Rifa={self.rifa_id} - #{self.number} -> {self.participante_id}"



class Compra(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    rifa = models.ForeignKey(Rifa, related_name='compras', on_delete=models.CASCADE)
    participante = models.ForeignKey(Participante, related_name='compras', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    # monto total pagado o a pagar por esta compra (moneda local)
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=100, blank=True)
    comprobante = models.ImageField(upload_to='comprobantes/', blank=True, null=True)
    referencia = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compra {self.id} - {self.participante_id} ({self.cantidad}) - {self.estado}"

    @property
    def badge_class(self):
        """Return bootstrap badge class name based on estado."""
        if self.estado == 'CONFIRMADO':
            return 'success'
        if self.estado == 'PENDIENTE':
            return 'warning'
        return 'danger'


class PaymentMethod(models.Model):
    nombre = models.CharField(max_length=200)
    detalles = models.TextField(blank=True, help_text='Instrucciones o datos para el pago, p.ej. número de cuenta, titular, nota')
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en', 'nombre']

    def __str__(self):
        return self.nombre


class PaymentMethodField(models.Model):
    metodo = models.ForeignKey(PaymentMethod, related_name='fields', on_delete=models.CASCADE)
    field_name = models.CharField(max_length=200)
    field_value = models.CharField(max_length=500)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"{self.metodo.nombre}: {self.field_name}"