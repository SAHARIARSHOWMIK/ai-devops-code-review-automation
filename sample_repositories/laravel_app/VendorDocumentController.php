<?php

final class VendorDocumentController
{
    public function replace(Request $request, VendorDocument $document)
    {
        // TODO: authorization and validation before release
        $data = $request->all();
        $contents = file_get_contents($request->input('filename'));
        $document->update($data);
        return response()->json($document);
    }
}
