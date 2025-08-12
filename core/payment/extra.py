# class BKashExecutePaymentView(views.APIView):
#     authentication_classes = []
#     permission_classes = []

#     def get(self, request, *args, **kwargs):
#         payment_id = request.query_params.get("paymentID") or request.query_params.get("paymentId")
#         if not payment_id:
#             return Response({"status": False, "message": "paymentID missing"}, status=400)
        
#         try:
#             invoice = Invoice.objects.get(bkash_payment_id=payment_id)
#         except Invoice.DoesNotExist:
#             return Response({"status": False, "message": "Invoice not found for paymentID"}, status=404)

#         client = BKashClient()
#         try:
#             exec_resp = client.execute_payment(payment_id)
#         except BKashError as e:
#             invoice.status = "failed"
#             invoice.save(update_fields=["status"])
#             return Response({"status": False, "message": str(e)}, status=502)

#         trx_id = exec_resp.get("trxID") or exec_resp.get("transactionID")
#         status_code = exec_resp.get("statusCode") or exec_resp.get("status")
#         status_msg = exec_resp.get("statusMessage") or exec_resp.get("message", "")
#         success = bool(trx_id) and str(status_code) in ("0000", "Success", "Completed", "200")

#         if success:
#             invoice.status = "paid"
#             invoice.bkash_trx_id = trx_id
#             invoice.save(update_fields=["status", "bkash_trx_id"])
#         else:
#             invoice.status = "failed"
#             invoice.save(update_fields=["status"])

#         redirect_to = f"{bkash.BKASH_CALLBACK_URL}?payment_uid={invoice.payment_uid}&result={'success' if success else 'failed'}"
#         return redirect(redirect_to)


